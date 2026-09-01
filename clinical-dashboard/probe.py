"""
probe.py — is it the API or the code?
Run from inside the clinical-dashboard folder:  python probe.py
One bare Gemini call. No Streamlit, no agents. Read line 3.
"""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()  # reads the .env in this folder
key = os.getenv("GEMINI_API_KEY")

print("1) Key found in .env:", bool(key))
if not key:
    raise SystemExit("   STOP: no key loaded. Put .env in THIS folder with GEMINI_API_KEY=your_key")
print("   Key length:", len(key))

MODEL = "models/gemini-flash-latest"  # same model the app uses
print("2) Calling", MODEL, "once...")

try:
    client = genai.Client(api_key=key)  # keep a reference; do NOT chain off this
    r = client.models.generate_content(
        model=MODEL, contents="Reply with exactly: OK"
    )
    print("3) SUCCESS — model replied:", repr(r.text))
    print("\n==> API + key WORK. The problem is in the app/agent code, not Gemini.")
except Exception as e:
    msg = str(e)
    print("3) FAILED:", type(e).__name__, "-", msg)
    low = msg.lower()
    if "503" in low or "unavailable" in low or "overload" in low:
        print("\n==> Google's side: Flash is overloaded. NOT your code. Wait and retry.")
    elif "429" in low or "quota" in low or "exhausted" in low:
        print("\n==> Free-tier quota used up. Wait for daily reset or use another key.")
    elif "403" in low or "permission" in low or "leaked" in low or "api_key" in low:
        print("\n==> Key problem: rotate/replace the key in .env.")
    else:
        print("\n==> Unexpected — paste this whole output back.")
