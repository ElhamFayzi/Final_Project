import os
import requests
from app.game_logic.judge import JudgeClientError

_DEFAULT_MODEL = "gemini-2.5-flash"
_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
_TIMEOUT_SECONDS = 30


def make_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise JudgeClientError("GEMINI_API_KEY is not set")

    model = os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)
    url = _ENDPOINT.format(model=model)

    def _call(system_text, user_text):
        payload = {
            "systemInstruction": {"parts": [{"text": system_text}]},
            "contents": [
                {"role": "user", "parts": [{"text": user_text}]},
            ],
            "generationConfig": {
                "temperature": 0.9,
                "responseMimeType": "application/json",
            },
        }
        headers = {"x-goog-api-key": api_key}
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (requests.RequestException, KeyError, IndexError) as exc:
            raise JudgeClientError(str(exc)) from exc

    return _call