from flask import Flask, request, jsonify
import requests
import json
import re

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

ALLOWED_ACTIONS = {
    "open_app",
    "open_chrome",
    "open_youtube",
    "open_google",
    "open_settings",
    "open_calculator",
    "none"
}


def ask_ollama(message, installed_apps):
    app_list_text = "\n".join(installed_apps[:300])

    prompt = f"""
You are JARVIS, a helpful Android phone AI assistant.

Understand:
- English
- Telugu
- Telugu written in English letters
- Telugu + English mixed language
- Different natural ways of saying the same thing

The user does NOT need to use exact commands.

Installed Android apps:
{app_list_text}

User message:
{message}

Your job:
1. Understand the user's meaning/context.
2. If the user wants to open an installed app, use:
   action = "open_app"
   app_name = exact installed app name
3. If the user wants Chrome/browser, use:
   action = "open_chrome"
4. If the user wants YouTube, use:
   action = "open_youtube"
5. If the user wants Google/search, use:
   action = "open_google"
6. If the user wants Android Settings, use:
   action = "open_settings"
7. If the user wants Calculator, use:
   action = "open_calculator"
8. For normal questions/conversation, use:
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

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        data = response.json()
        raw = data.get("response", "").strip()

        print("OLLAMA RAW:", raw)

        # JSON block extraction
        match = re.search(r"\{.*\}", raw, re.DOTALL)

        if not match:
            return {
                "reply": raw if raw else "Sorry sir, answer dorakaledu.",
                "action": "none",
                "app_name": ""
            }

        result = json.loads(match.group(0))

        action = result.get("action", "none")
        app_name = result.get("app_name", "")
        reply = result.get("reply", "Okay sir.")

        if action not in ALLOWED_ACTIONS:
            action = "none"

        return {
            "reply": str(reply),
            "action": action,
            "app_name": str(app_name)
        }

    except Exception as e:
        print("OLLAMA ERROR:", e)

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

        message = str(data.get("message", "")).strip()
        installed_apps = data.get("installed_apps", [])

        if not isinstance(installed_apps, list):
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
        print("INSTALLED APPS:", len(installed_apps))

        # Direct app detection for natural open commands
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
            app_label = str(installed).strip()

            if not app_label:
                continue

            if app_label.lower() in message_lower:

                print(
                    "APP DETECTED:",
                    app_label,
                    "| MESSAGE:",
                    message
                )

                if any(word in message_lower for word in open_words):

                    print(
                        "ACTION: open_app",
                        "| APP:",
                        app_label
                    )

                    return jsonify({
                        "reply": f"{app_label} open chesthunnanu sir.",
                        "action": "open_app",
                        "app_name": app_label
                    })

        # Ask AI brain
        result = ask_ollama(
            message,
            installed_apps
        )

        action = result.get("action", "none")
        app_name = result.get("app_name", "")
        reply = result.get("reply", "Okay sir.")

        # Verify app name before allowing open_app
        if action == "open_app":

            matched_app = None

            for installed in installed_apps:
                if installed.lower() == app_name.lower():
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
                reply = "Aa app phone lo kanipinchaledu sir."

        print(
            "JARVIS RESPONSE:",
            action,
            "|",
            app_name
        )

        return jsonify({
            "reply": reply,
            "action": action,
            "app_name": app_name
        })

    except Exception as e:

        print(
            "SERVER ERROR:",
            e
        )

        return jsonify({
            "reply": "Sorry sir, oka technical problem vachindi.",
            "action": "none",
            "app_name": ""
        }), 500


if __name__ == "__main__":

    print("===================================")
    print("        JARVIS BRAIN ONLINE")
    print("===================================")
    print("Model:", MODEL)
    print("Server: http://192.168.0.18:5000")
    print("===================================")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )