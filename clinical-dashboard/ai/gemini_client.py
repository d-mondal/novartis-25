import os
from dotenv import load_dotenv
from google import genai

# Load env variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY missing")

# Create client
client = genai.Client(api_key=API_KEY)

MODEL_NAME = "models/gemini-flash-latest"  # ✅ FREE & FAST

def gemini_call(prompt: str) -> str:
    """
    Calls Gemini using the new google.genai SDK
    """
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"[Gemini Error] {str(e)}"
