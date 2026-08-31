# # check_quota.py
# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# api_key = os.getenv("GEMINI_API_KEY")
# if not api_key:
#     print("❌ No API key found in .env")
#     exit()

# # Test with minimal request
# url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

# payload = {
#     "contents": [{
#         "parts": [{
#             "text": "Hello, just testing."
#         }]
#     }]
# }

# try:
#     response = requests.post(url, json=payload, timeout=10)
#     print(f"Status Code: {response.status_code}")
#     print(f"Response: {response.text[:200]}")
# except Exception as e:
#     print(f"Error: {e}")
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("\nAVAILABLE MODELS:\n")
for m in genai.list_models():
    print(m.name, "->", m.supported_generation_methods)
