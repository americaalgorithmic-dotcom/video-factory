import os, re, json, random, subprocess, asyncio, requests, edge_tts

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
PIXABAY_KEY = os.environ["PIXABAY_API_KEY"]
MODEL = "gemini-3.8-flash"
SCENES = 6
VOICE = "en-US-GuyNeural"
OUT = "output"
os.makedirs(OUT, exist_ok=True)

def ask(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    r = requests.post(url, headers={"x-goog-api-key": GEMINI_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json"}}, timeout=120)
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)

topics = [t.strip() for t in open("topics.txt") if t.strip()]
done = set(l.strip() for l in open("done.txt")) if os.path.exists("done.txt") else set()
todo = [t for t in topics if t not in done]
if not todo:
    raise SystemExit("No topics left")
topic = todo[0]

script = ask(f"""Write a documentary-style YouTube script about: {topic}.
Use only well-established historical facts. If unsure about a date, name or number, leave it out.
Return JSON: {{"title": "...", "description": "...", "scenes": [{{"narration": "about 60 words", "keyword": "one or two English words for stock footage"}}]}} with exactly {SCENES} scenes.""")
script = ask("Fact-check this script. Remove or fix any claim that is wrong or uncertain. "
             "Keep the same JSON structure and scene count. Return only JSON.\n" + json.dumps(script))

async def speak(text, path):
    await edge_tts.Communicate(text, VOICE).save(path)

def get_clip(keyword, path):
    for q in (keyword, "american landscape"):
        r = requests.get("https://pixabay.com/api/videos/",
            params={"key": PIXABAY_KEY, "q": q, "per_page": 10}, timeout=60).json()
        hits = r.get("hits", [])
        if hits:
            h = random.choice(hits[:5])
            v = h["videos"].get("medium") or h["videos"]["small"]
            open(path, "wb").write(requests.get(v["url"], timeout=120).content)
            return
    raise RuntimeError("no clip found")

parts = []
for i, s in enumerate(script["scenes"]):
    a, c, p = f"{OUT}/a{i}.mp3", f"{OUT}/c{i}.mp4", f"{OUT}/s{i}.mp4"
    asyncio.run(speak(s["narration"], a))
    get_clip(s["keyword"], c)
    subprocess.run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", c, "-i", a,
        "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30,format=yuv420p",
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", p], check=True)
    parts.append(p)

with open(f"{OUT}/list.txt", "w") as f:
    for p in parts:
        f.write(f"file '{os.path.basename(p)}'\n")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt",
    "-c", "copy", f"{OUT}/video.mp4"], check=True)

open(f"{OUT}/title.txt", "w").write(script["title"])
open(f"{OUT}/description.txt", "w").write(script["description"])
print("Done:", script["title"])
