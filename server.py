from flask import Flask, request, jsonify
import os
import json
import requests
import time

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    ""
).strip()

# Primary model
MODEL = "gemini-3.5-flash-lite"

# Fallback model for temporary 503
FALLBACK_MODEL = "gemini-3.1-flash-lite"

GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models"
)

# Reuse HTTP connection
SESSION = requests.Session()

SESSION.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json",
    "x-goog-api-key": GEMINI_API_KEY
})


# =========================================================
# STANDARD RESPONSE
# =========================================================

def jarvis_response(
    reply="",
    action="none",
    app_name=""
):
    return {
        "reply": reply,
        "action": action,
        "app_name": app_name
    }


# =========================================================
# GEMINI REQUEST
# =========================================================

def call_gemini_model(
    model,
    payload,
    retries=2
):

    url = (
        f"{GEMINI_BASE_URL}/"
        f"{model}:generateContent"
    )

    for attempt in range(retries + 1):

        try:

            print("-----------------------------------")
            print("GEMINI REQUEST")
            print("MODEL:", model)
            print("ATTEMPT:", attempt + 1)

            response = SESSION.post(
                url,
                json=payload,
                timeout=(5, 20)
            )

            print(
                "GEMINI STATUS:",
                response.status_code
            )

            # =================================================
            # SUCCESS
            # =================================================

            if response.status_code == 200:
                return response

            # =================================================
            # TEMPORARY 503
            # =================================================

            if response.status_code == 503:

                print(
                    "GEMINI 503:",
                    response.text[:1000]
                )

                if attempt < retries:

                    delay = 1.5 * (
                        2 ** attempt
                    )

                    print(
                        f"503 retrying in "
                        f"{delay:.1f} seconds..."
                    )

                    time.sleep(delay)

                    continue

                return response

            # =================================================
            # OTHER HTTP ERRORS
            # =================================================

            print(
                "GEMINI HTTP ERROR:",
                response.text[:1000]
            )

            return response

        except requests.Timeout:

            print(
                "GEMINI TIMEOUT ON MODEL:",
                model
            )

            if attempt < retries:

                delay = 1.5 * (
                    2 ** attempt
                )

                print(
                    f"Timeout retrying in "
                    f"{delay:.1f} seconds..."
                )

                time.sleep(delay)

                continue

            raise

        except requests.RequestException as e:

            print(
                "NETWORK ERROR:",
                repr(e)
            )

            if attempt < retries:

                delay = 1.5 * (
                    2 ** attempt
                )

                print(
                    f"Network retrying in "
                    f"{delay:.1f} seconds..."
                )

                time.sleep(delay)

                continue

            raise

    return None


# =========================================================
# GEMINI
# =========================================================

def ask_gemini(
    message,
    installed_apps
):

    if not GEMINI_API_KEY:

        return jarvis_response(
            "Sir, Gemini API key configure avvaledu."
        )

    apps_text = (
        ", ".join(installed_apps)
        if installed_apps
        else "None"
    )

    # =====================================================
    # STRICT JARVIS PROMPT
    # =====================================================

    prompt = f"""
You are JARVIS, a fast personal Android voice assistant.

User:
{message}

Installed apps:
{apps_text}

Give a short natural answer.

IMPORTANT BEHAVIOR:

1. Normal questions, topics, movies, people, places,
   general knowledge, explanations and conversations
   MUST be answered directly.

2. NEVER open Google or Chrome just because the user
   mentions a topic.

3. A topic is NOT a search command.

4. Examples of NORMAL QUESTIONS:

"Marvel movies"
→ Give information about Marvel movies.

"Tell me about Marvel"
→ Answer about Marvel.

"Who is Iron Man?"
→ Answer directly.

"What are the Avengers?"
→ Answer directly.

"Latest Marvel movie"
→ Answer normally unless the user explicitly asks
  to search Google.

5. Google/Chrome actions are allowed ONLY when the user
   explicitly asks to search, browse, open Google, or
   open Chrome.

6. Examples of EXPLICIT SEARCH/ACTION COMMANDS:

"Open Google"
→ action = open_google

"Open Chrome"
→ action = open_chrome

"Search Marvel movies on Google"
→ action = open_google

"Search for Marvel movies"
→ action = open_google

"Google Marvel movies"
→ action = open_google

7. If the user only mentions a topic, answer it.
   Do NOT convert it into a search action.

8. If there is no clear action request,
   action MUST be "none".

9. Keep answers short because JARVIS is a voice assistant.

AVAILABLE ACTIONS:

open_chrome
open_youtube
open_google
open_settings
open_calculator
open_app
volume_up
volume_down
volume_mute
ringer_normal
ringer_silent
ringer_vibrate
wifi_settings
bluetooth_settings
alarm
timer
none

STRICT ACTION RULE:

Use an action ONLY when the user's words clearly
and explicitly request that action.

For open_app:
app_name must contain the requested app name.

IMPORTANT:

Do not invent an action.

Do not use open_google for normal questions.

Do not use open_chrome for normal questions.

Return ONLY valid JSON.

JSON FORMAT:

{{
  "reply": "short natural answer",
  "action": "none",
  "app_name": ""
}}
"""

    # =====================================================
    # GEMINI PAYLOAD
    # =====================================================

    payload = {

        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],

        "generationConfig": {

            "maxOutputTokens": 120,

            "responseMimeType":
                "application/json",

            "thinkingConfig": {
                "thinkingLevel": "minimal"
            }
        }
    }

    try:

        print("===================================")
        print("JARVIS → GEMINI")
        print("PRIMARY MODEL:", MODEL)
        print(
            "FALLBACK MODEL:",
            FALLBACK_MODEL
        )
        print(
            "MESSAGE:",
            message
        )

        # =================================================
        # PRIMARY MODEL
        # =================================================

        response = call_gemini_model(
            MODEL,
            payload,
            retries=2
        )

        # =================================================
        # FALLBACK MODEL ON 503
        # =================================================

        if (
            response is not None
            and response.status_code == 503
        ):

            print("===================================")
            print(
                "PRIMARY MODEL STILL 503"
            )
            print(
                "SWITCHING TO FALLBACK MODEL"
            )
            print(
                "FALLBACK:",
                FALLBACK_MODEL
            )
            print("===================================")

            response = call_gemini_model(
                FALLBACK_MODEL,
                payload,
                retries=1
            )

        # =================================================
        # NO RESPONSE
        # =================================================

        if response is None:

            return jarvis_response(
                "Sir, Gemini connection problem."
            )

        # =================================================
        # FINAL HTTP ERROR
        # =================================================

        if response.status_code != 200:

            print(
                "FINAL GEMINI ERROR:",
                response.text[:1000]
            )

            if response.status_code == 503:

                return jarvis_response(
                    "Sir, Gemini is temporarily unavailable. Please try again."
                )

            if response.status_code == 429:

                return jarvis_response(
                    "Sir, Gemini request limit reached. Please try again shortly."
                )

            if response.status_code in (
                401,
                403
            ):

                return jarvis_response(
                    "Sir, Gemini API authorization problem."
                )

            return jarvis_response(
                f"Gemini error HTTP "
                f"{response.status_code}"
            )

        # =================================================
        # PARSE RESPONSE
        # =================================================

        data = response.json()

        candidates = data.get(
            "candidates",
            []
        )

        if not candidates:

            return jarvis_response(
                "Sir, Gemini response empty ga vachindi."
            )

        content = candidates[0].get(
            "content",
            {}
        )

        parts = content.get(
            "parts",
            []
        )

        if not parts:

            return jarvis_response(
                "Sir, Gemini response empty ga vachindi."
            )

        text = parts[0].get(
            "text",
            ""
        ).strip()

        if not text:

            return jarvis_response(
                "Sir, response empty ga vachindi."
            )

        print(
            "GEMINI RAW:",
            text
        )

        # =================================================
        # CLEAN JSON MARKDOWN
        # =================================================

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )

        text = text.strip()

        # =================================================
        # JSON PARSE
        # =================================================

        result = json.loads(text)

        reply = str(
            result.get(
                "reply",
                "I couldn't get a response."
            )
        ).strip()

        action = str(
            result.get(
                "action",
                "none"
            )
        ).strip()

        app_name = str(
            result.get(
                "app_name",
                ""
            )
        ).strip()

        # =================================================
        # ACTION SAFETY
        # =================================================

        allowed_actions = {
            "open_chrome",
            "open_youtube",
            "open_google",
            "open_settings",
            "open_calculator",
            "open_app",
            "volume_up",
            "volume_down",
            "volume_mute",
            "ringer_normal",
            "ringer_silent",
            "ringer_vibrate",
            "wifi_settings",
            "bluetooth_settings",
            "alarm",
            "timer",
            "none"
        }

        if action not in allowed_actions:

            action = "none"

        return jarvis_response(
            reply,
            action,
            app_name
        )

    # =====================================================
    # TIMEOUT
    # =====================================================

    except requests.Timeout:

        print(
            "GEMINI TIMEOUT"
        )

        return jarvis_response(
            "Sir, Gemini response time ayipoyindi."
        )

    # =====================================================
    # NETWORK ERROR
    # =====================================================

    except requests.RequestException as e:

        print(
            "NETWORK ERROR:",
            repr(e)
        )

        return jarvis_response(
            "Sir, Gemini network connection problem."
        )

    # =====================================================
    # JSON ERROR
    # =====================================================

    except json.JSONDecodeError as e:

        print(
            "JSON ERROR:",
            repr(e)
        )

        return jarvis_response(
            "Sir, Gemini response format problem."
        )

    # =====================================================
    # OTHER ERROR
    # =====================================================

    except Exception as e:

        print(
            "GEMINI ERROR:",
            repr(e)
        )

        return jarvis_response(
            "Sir, Gemini response lo problem vachindi."
        )


# =========================================================
# HOME
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return "JARVIS Brain is Running!"


# =========================================================
# CHAT
# =========================================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        message = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        installed_apps = data.get(
            "installed_apps",
            []
        )

        if not isinstance(
            installed_apps,
            list
        ):
            installed_apps = []

        if not message:

            return jsonify(
                jarvis_response(
                    "Sir, command vinipinchaledu."
                )
            )

        lower = message.lower()

        # =================================================
        # FAST LOCAL COMMANDS
        # =================================================

        if (
            "open chrome" in lower
            or "chrome open" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Opening Chrome, sir.",
                    "open_chrome"
                )
            )

        if (
            "open youtube" in lower
            or "youtube open" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Opening YouTube, sir.",
                    "open_youtube"
                )
            )

        if (
            "open google" in lower
            or "google open" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Opening Google, sir.",
                    "open_google"
                )
            )

        if (
            "open settings" in lower
            or "settings open" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Opening Settings, sir.",
                    "open_settings"
                )
            )

        if (
            "open calculator" in lower
            or "calculator open" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Opening Calculator, sir.",
                    "open_calculator"
                )
            )

        if (
            "volume up" in lower
            or "increase volume" in lower
            or "increase the volume" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Increasing volume, sir.",
                    "volume_up"
                )
            )

        if (
            "volume down" in lower
            or "decrease volume" in lower
            or "decrease the volume" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Decreasing volume, sir.",
                    "volume_down"
                )
            )

        if (
            "mute volume" in lower
            or "volume mute" in lower
            or lower == "mute"
        ):

            return jsonify(
                jarvis_response(
                    "Muting volume, sir.",
                    "volume_mute"
                )
            )

        if (
            "wifi settings" in lower
            or "open wifi" in lower
            or "open wi-fi" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Opening Wi-Fi settings, sir.",
                    "wifi_settings"
                )
            )

        if (
            "bluetooth settings" in lower
            or "open bluetooth" in lower
        ):

            return jsonify(
                jarvis_response(
                    "Opening Bluetooth settings, sir.",
                    "bluetooth_settings"
                )
            )

        # =================================================
        # EVERYTHING ELSE → GEMINI
        # =================================================

        result = ask_gemini(
            message,
            installed_apps
        )

        return jsonify(
            result
        )

    except Exception as e:

        print(
            "SERVER ERROR:",
            repr(e)
        )

        return jsonify(
            jarvis_response(
                f"Server error: "
                f"{type(e).__name__}"
            )
        ), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print("")
    print("===================================")
    print("       JARVIS BACKEND ONLINE")
    print("===================================")
    print(
        "PRIMARY MODEL:",
        MODEL
    )
    print(
        "FALLBACK MODEL:",
        FALLBACK_MODEL
    )
    print(
        "GEMINI API:",
        "CONFIGURED"
        if GEMINI_API_KEY
        else "NOT CONFIGURED"
    )
    print(
        "PORT:",
        port
    )
    print("===================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=port
    )
