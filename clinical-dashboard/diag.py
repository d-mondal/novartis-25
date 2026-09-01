"""
diag.py — run from the clinical-dashboard folder:  python diag.py
Reads your real gemini_client, lists valid model names, makes one call.
Paste the whole output back.
"""
from ai.gemini_client import client, MODEL_NAME, gemini_call

print("1) MODEL_NAME your app is configured to use:", MODEL_NAME)

print("\n2) Model names your key actually accepts (containing 'flash'):")
try:
    found = False
    for m in client.models.list():
        name = getattr(m, "name", str(m))
        if "flash" in name.lower():
            print("   ", name)
            found = True
    if not found:
        print("    (no flash models listed — printing all instead)")
        for m in client.models.list():
            print("   ", getattr(m, "name", str(m)))
except Exception as e:
    print("    could not list models:", type(e).__name__, "-", str(e)[:120])

print("\n3) One test call through your app's real path:")
print("   ->", gemini_call("Reply with exactly: OK"))