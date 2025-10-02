import openai
import sys

print("🐍 Python version:", sys.version)
print("📦 OpenAI package version:", openai.__version__)

try:
    # Δοκιμή νέου client API
    from openai import OpenAI
    client = OpenAI()
    print("✅ Νέο API διαθέσιμο: OpenAI() client ok")
except Exception as e:
    print("❌ Νέο API (OpenAI client) ΔΕΝ παίζει:", e)

try:
    # Δοκιμή παλιού API style
    resp = openai.ChatCompletion
    print("✅ Παλιό API διαθέσιμο: openai.ChatCompletion ok")
except Exception as e:
    print("❌ Παλιό API ΔΕΝ παίζει:", e)
