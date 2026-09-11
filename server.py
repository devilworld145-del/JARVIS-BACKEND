from flask import Flask, request, jsonify
import requests
import json
import re
import os

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.8-flash:generateContent"
)

MODEL = "gemini-3.8-flash"

ALLOWED_ACTIONS = {
    "open_app",
    "open_chrome",
    "open_youtube",
    "open_google",
    "open_settings",
    "open_calculator",
    "none"
}


def ask_gemini(message, installed_apps):

    app_list_text = "\n".join(installed_apps[:300])

    prompt = f"""
You are JARVIS, a helpful Android phone AI assistant.

Understand:
- English
- Telugu
- Telugu written in English letters
- Telugu + English mixed language
- Natural conversational language

Keep replies SHORT and natural.

Installed Android apps:
{app_list_text}

User message:
{message}

Your job:

1. If the user wants to open an installed app:
   action = "open_app"
   app_name = exact installed app name

2. If the user wants Chrome or browser:
   action = "open_chrome"

3. If the user wants YouTube:
   action = "open_youtube"

4. If the user wants Google/search:
   action = "open_google"

5. If the user wants Android Settings:
   action = "open_settings"

6. If the user wants Calculator:
   action = "open_calculator"

7. For normal questions or conversation:
   action = "none"

Examples:

"Open WhatsApp"
=> open_app, app_name = WhatsApp

"WhatsApp open cheyyi"
=> open_app, app_name = WhatsApp

"Whatsapp loki teesukellu"
=> open_app, app_name = WhatsApp

"Chrome open chey"
=> open_chrome

"Browser open cheyyi"
=> open_chrome

"YouTube ki teesukellu"
=> open_youtube

"Google lo search cheyyali"
=> open_google

"Settings open cheyyi"
=> open_settings

"Calculator kavali"
=> open_calculator

"Who is Iron Man?"
=> none

"Naaku oka joke cheppu"
=> none

Return ONLY valid JSON in exactly this format:

{{
  "reply": "short natural response",
  "action": "open_app/open_chrome/open_youtube/open_google/open_settings/open_calculator/none",
  "app_name": "exact installed app name or empty string"
}}
"""

    if not GEMINI_API_KEY:
        print("GEMINI ERROR: GEMINI_API_KEY is missing")

        return {
            "reply": "Sir, Gemini key configure avvaledu.",
            "action": "none",
            "app_name": ""
        }

    try:

        response = requests.post(
            GEMINI_URL,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json"
            },
            json={
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
                    "temperature": 0.3,
                    "maxOutputTokens": 300,
                    "responseMimeType": "application/json"
                }
            },
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        raw = (
            data["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
        ).strip()

        print("GEMINI RAW:", raw)

        match = re.search(
            r"\{.*\}",
            raw,
            re.DOTALL
        )

        if not match:

            return {
                "reply": raw if raw else "Sorry sir, answer dorakaledu.",
                "action": "none",
                "app_name": ""
            }

        result = json.loads(match.group(0))

        action = result.get(
            "action",
            "none"
        )

        app_name = result.get(
            "app_name",
            ""
        )

        reply = result.get(
            "reply",
            "Okay sir."
        )

        if action not in ALLOWED_ACTIONS:
            action = "none"

        return {
            "reply": str(reply),
            "action": action,
            "app_name": str(app_name)
        }

    except Exception as e:

        print("GEMINI ERROR:", e)

        return {
            "reply": "Sorry sir, JARVIS brain ki connect avvalekapoyanu.",
            "action": "none",
            "app_name": ""
        }


@app.route("/")
def home():

    return "JARVIS Brain is Running!"


@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json(force=True)

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

        installed_apps = [
            str(app).strip()
            for app in installed_apps
            if str(app).strip()
        ]

        if not message:

            return jsonify({
                "reply": "Em cheyyali sir?",
                "action": "none",
                "app_name": ""
            })

        print("\nUSER:", message)

        print(
            "INSTALLED APPS:",
            len(installed_apps)
        )

        message_lower = message.lower()

        open_words = [
            "open",
            "launch",
            "start",
            "go to",
            "open cheyyi",
            "open chey",
            "teesukellu",
            "loki teesukellu",
            "kavali"
        ]

        for installed in installed_apps:

            app_label = str(
                installed
            ).strip()

            if not app_label:
                continue

            if app_label.lower() in message_lower:

                print(
                    "APP DETECTED:",
                    app_label,
                    "| MESSAGE:",
                    message
                )

                if any(
                    word in message_lower
                    for word in open_words
                ):

                    print(
                        "ACTION: open_app",
                        "| APP:",
                        app_label
                    )

                    return jsonify({
                        "reply":
                            f"{app_label} open chesthunnanu sir.",
                        "action":
                            "open_app",
                        "app_name":
                            app_label
                    })

        result = ask_gemini(
            message,
            installed_apps
        )

        action = result.get(
            "action",
            "none"
        )

        app_name = result.get(
            "app_name",
            ""
        )

        reply = result.get(
            "reply",
            "Okay sir."
        )

        if action == "open_app":

            matched_app = None

            for installed in installed_apps:

                if (
                    installed.lower()
                    == app_name.lower()
                ):

                    matched_app = installed
                    break

            if matched_app:

                app_name = matched_app

                print(
                    "VERIFIED APP:",
                    app_name
                )

            else:

                print(
                    "APP NOT FOUND:",
                    app_name
                )

                action = "none"

                app_name = ""

                reply = (
                    "Aa app phone lo "
                    "kanipinchaledu sir."
                )

        print(
            "JARVIS RESPONSE:",
            action,
            "|",
            app_name
        )

        return jsonify({

            "reply":
                reply,

            "action":
                action,

            "app_name":
                app_name
        })

    except Exception as e:

        print(
            "SERVER ERROR:",
            e
        )

        return jsonify({

            "reply":
                "Sorry sir, oka technical problem vachindi.",

            "action":
                "none",

            "app_name":
                ""
        }), 500


if __name__ == "__main__":

    print(
        "==================================="
    )

    print(
        "        JARVIS BRAIN ONLINE"
    )

    print(
        "==================================="
    )

    print(
        "Model:",
        MODEL
    )

    print(
        "Gemini API:",
        "Configured"
        if GEMINI_API_KEY
        else "MISSING"
    )

    print(
        "==================================="
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
