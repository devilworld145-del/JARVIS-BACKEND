from flask import Flask, request, jsonify
import os
import json
import requests

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODEL = "gemini-3.8-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/"
    f"v1beta/models/{MODEL}:generateContent"
)


def ask_gemini(message, installed_apps):
    if not GEMINI_API_KEY:
        return {
            "reply": "Sir, Gemini API key configure avvaledu.",
            "action": "none",
            "app_name": ""
        }

    apps_text = ", ".join(installed_apps) if installed_apps else "None"

    prompt = f"""
You are JARVIS, a personal Android assistant.

User said:
{message}

Installed Android apps:
{apps_text}

Reply naturally and briefly.

If the user wants an Android action, choose one of these actions:

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

For open_app, put the requested app name in app_name.

Return ONLY valid JSON in exactly this format:

{{
  "reply": "short natural response",
  "action": "none",
  "app_name": ""
}}

Do not use markdown.
Do not add extra text.
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
            "temperature": 0.3,
            "maxOutputTokens": 300,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(
            GEMINI_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY
            },
            json=payload,
            timeout=120
        )

        print("GEMINI STATUS:", response.status_code)
        print("GEMINI RESPONSE:", response.text)

        if response.status_code != 200:
            return {
                "reply": f"Gemini error HTTP {response.status_code}",
                "action": "none",
                "app_name": ""
            }

        data = response.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]

        result = json.loads(text)

        return {
            "reply": str(result.get("reply", "")),
            "action": str(result.get("action", "none")),
            "app_name": str(result.get("app_name", ""))
        }

    except Exception as e:
        print("GEMINI ERROR:", repr(e))

        return {
            "reply": f"Gemini connection error: {type(e).__name__}",
            "action": "none",
            "app_name": ""
        }


@app.route("/", methods=["GET"])
def home():
    return "JARVIS Brain is Running!"


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}

        message = str(data.get("message", "")).strip()
        installed_apps = data.get("installed_apps", [])

        if not message:
            return jsonify({
                "reply": "Sir, command vinipinchaledu.",
                "action": "none",
                "app_name": ""
            })

        # Direct commands first
        lower = message.lower()

        if "open chrome" in lower or "chrome open" in lower:
            return jsonify({
                "reply": "Opening Chrome, sir.",
                "action": "open_chrome",
                "app_name": ""
            })

        if "open youtube" in lower or "youtube open" in lower:
            return jsonify({
                "reply": "Opening YouTube, sir.",
                "action": "open_youtube",
                "app_name": ""
            })

        if "open google" in lower or "google open" in lower:
            return jsonify({
                "reply": "Opening Google, sir.",
                "action": "open_google",
                "app_name": ""
            })

        if "open settings" in lower or "settings open" in lower:
            return jsonify({
                "reply": "Opening Settings, sir.",
                "action": "open_settings",
                "app_name": ""
            })

        if "calculator open" in lower or "open calculator" in lower:
            return jsonify({
                "reply": "Opening Calculator, sir.",
                "action": "open_calculator",
                "app_name": ""
            })

        if "volume up" in lower or "increase volume" in lower:
            return jsonify({
                "reply": "Increasing volume, sir.",
                "action": "volume_up",
                "app_name": ""
            })

        if "volume down" in lower or "decrease volume" in lower:
            return jsonify({
                "reply": "Decreasing volume, sir.",
                "action": "volume_down",
                "app_name": ""
            })

        if "mute" in lower:
            return jsonify({
                "reply": "Muting volume, sir.",
                "action": "volume_mute",
                "app_name": ""
            })

        if "wifi settings" in lower or "open wifi" in lower:
            return jsonify({
                "reply": "Opening Wi-Fi settings, sir.",
                "action": "wifi_settings",
                "app_name": ""
            })

        if "bluetooth settings" in lower or "open bluetooth" in lower:
            return jsonify({
                "reply": "Opening Bluetooth settings, sir.",
                "action": "bluetooth_settings",
                "app_name": ""
            })

        # Otherwise ask Gemini
        result = ask_gemini(message, installed_apps)

        return jsonify(result)

    except Exception as e:
        print("SERVER ERROR:", repr(e))

        return jsonify({
            "reply": f"Server error: {type(e).__name__}",
            "action": "none",
            "app_name": ""
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    print("===================================")
    print("       JARVIS BACKEND ONLINE")
    print("===================================")
    print("Model:", MODEL)
    print("Gemini API:", "Configured" if GEMINI_API_KEY else "NOT CONFIGURED")
    print("Port:", port)

    app.run(
        host="0.0.0.0",
        port=port
    )
