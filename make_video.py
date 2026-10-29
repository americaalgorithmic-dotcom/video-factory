import os, re, json, random, subprocess, asyncio, requests, edge_tts

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
PIXABAY_KEY = os.environ["PIXABAY_API_KEY"]
MODEL = "gemini-3.8-flash"
SCENES = 6
VOICE = "en-US-GuyNeural"
OUT = "output"
os.makedirs(OUT, exist_ok=True)


def ask(prompt):
    import time

    url = (
        f"https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL}:generateContent"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 4096
        }
    }

    for attempt in range(3):
        try:
            r = requests.post(
                url,
                headers={"x-goog-api-key": GEMINI_KEY},
                json=payload,
                timeout=(15, 120)
            )

            if r.status_code in (408, 429, 500, 502, 503, 504):
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue

            r.raise_for_status()

            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = re.sub(
                r"^```(?:json)?|```$",
                "",
                text.strip(),
                flags=re.M
            ).strip()

            return json.loads(text)

        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))

    raise RuntimeError("Gemini API failed after retries")

