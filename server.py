from flask import Flask, request, jsonify
import os
import json
import requests
import time

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Primary model
MODEL = "gemini-3.5-flash-lite"

# Fallback model if Gemini temporarily returns HTTP 503
FALLBACK_MODEL = "gemini-3.1-flash-lite"

GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models"
)

# Reuse HTTP connection for better latency
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

def call_gemini_model(model, payload, retries=2):

    url = f"{GEMINI_BASE_URL}/{model}:generateContent"

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

            print("GEMINI STATUS:", response.status_code)

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            if response.status_code == 200:
                return response

            # -------------------------------------------------
            # TEMPORARY SERVER OVERLOAD / UNAVAILABLE
            # Google recommends exponential backoff for 503.
            # -------------------------------------------------

            if response.status_code == 503:

                print(
                    "GEMINI 503:",
                    response.text[:1000]
                )

                if attempt < retries:

                    delay = 1.5 * (2 ** attempt)

                    print(
                        f"503 retrying in {delay:.1f} seconds..."
                    )

                    time.sleep(delay)
                    continue

                return response

            # -------------------------------------------------
            # Other HTTP errors
            # -------------------------------------------------

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

                delay = 1.5 * (2 ** attempt)

                print(
                    f"Timeout retrying in {delay:.1f} seconds..."
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

                delay = 1.5 * (2 ** attempt)

                print(
                    f"Network retrying in {delay:.1f} seconds..."
                )

                time.sleep(delay)
                continue

            raise

    return None


# =========================================================
# GEMINI
# =========================================================

def ask_gemini(message, installed_apps):

    if not GEMINI_API_KEY:

        return jarvis_response(
            "Sir, Gemini API key configure avvaledu."
        )

    apps_text = ", ".join(
        installed_apps
    ) if installed_apps else "None"

    # Short prompt = less input processing
    prompt = f"""
You are JARVIS, a fast personal Android voice assistant.

User:
{message}

Installed apps:
{apps_text}

Give a short natural answer.

Available actions:
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

Use an action only when the user clearly requests it.

For open_app:
app_name must contain the requested app name.

Return ONLY this JSON:
{{
  "reply": "short answer",
  "action": "none",
  "app_name": ""
}}
"""

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
            "responseMimeType": "application/json",
            "thinkingConfig": {
                "thinkingLevel": "minimal"
            }
        }
    }

    try:

        print("===================================")
        print("JARVIS → GEMINI")
        print("PRIMARY MODEL:", MODEL)
        print("FALLBACK MODEL:", FALLBACK_MODEL)
        print("MESSAGE:", message)

        # =====================================================
        # 1. PRIMARY MODEL
        # =====================================================

        response = call_gemini_model(
            MODEL,
            payload,
            retries=2
        )

        # =====================================================
        # 2. IF PRIMARY RETURNS 503,
        #    AUTOMATICALLY TRY FALLBACK MODEL
        # =====================================================

        if response is not None and response.status_code == 503:

            print("===================================")
            print("PRIMARY GEMINI MODEL STILL 503")
            print("SWITCHING TO FALLBACK MODEL")
            print("FALLBACK:", FALLBACK_MODEL)
            print("===================================")

            response = call_gemini_model(
                FALLBACK_MODEL,
                payload,
                retries=1
            )

        # =====================================================
        # 3. FINAL HTTP ERROR
        # =====================================================

        if response is None:

            return jarvis_response(
                "Sir, Gemini connection problem."
            )

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

            if response.status_code in (401, 403):

                return jarvis_response(
                    "Sir, Gemini API authorization problem."
                )

            return jarvis_response(
                f"Gemini error HTTP {response.status_code}"
            )

        # =====================================================
        # 4. PARSE GEMINI RESPONSE
        # =====================================================

        data = response.json()

        candidates = data.get(
            "candidates",
            []
        )

        if not candidates:

            return jarvis_response(
                "Sir, Gemini response empty ga vachindi."
            )

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
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

        print("GEMINI RAW:", text)

        # Safety cleanup if model accidentally adds markdown
        text = text.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

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

        return jarvis_response(
            reply,
            action,
            app_name
        )

    except requests.Timeout:

        print("GEMINI TIMEOUT")

        return jarvis_response(
            "Sir, Gemini response time ayipoyindi."
        )

    except requests.RequestException as e:

        print(
            "NETWORK ERROR:",
            repr(e)
        )

        return jarvis_response(
            "Sir, Gemini network connection problem."
        )

    except json.JSONDecodeError as e:

        print(
            "JSON ERROR:",
            repr(e)
        )

        return jarvis_response(
            "Sir, Gemini response format problem."
        )

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

@app.route("/", methods=["GET"])
def home():

    return "JARVIS Brain is Running!"


# =========================================================
# CHAT
# =========================================================

@app.route("/chat", methods=["POST"])
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
        # No Gemini call needed
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
        # GEMINI
        # =================================================

        result = ask_gemini(
            message,
            installed_apps
        )

        return jsonify(result)

    except Exception as e:

        print(
            "SERVER ERROR:",
            repr(e)
        )

        return jsonify(
            jarvis_response(
                f"Server error: {type(e).__name__}"
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
    print("PRIMARY MODEL:", MODEL)
    print("FALLBACK MODEL:", FALLBACK_MODEL)
    print(
        "GEMINI API:",
        "CONFIGURED"
        if GEMINI_API_KEY
        else "NOT CONFIGURED"
    )
    print("PORT:", port)
    print("===================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=port
    )
