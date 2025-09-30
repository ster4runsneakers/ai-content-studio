import os, requests
from dotenv import load_dotenv

# Φόρτωσε .env
load_dotenv()

token = os.getenv("REPLICATE_API_TOKEN")
if not token:
    print("❌ Δεν βρέθηκε το REPLICATE_API_TOKEN στο .env")
    exit(1)

print("DEBUG TOKEN:", token[:8] + "...")

# Δοκίμασε να φέρεις τις εκδόσεις του SDXL
url = "https://api.replicate.com/v1/models/stability-ai/sdxl/versions"
headers = {"Authorization": f"Token {token}"}

r = requests.get(url, headers=headers)

print("STATUS:", r.status_code)
print("BODY:", r.text[:500])  # δείχνουμε μόνο τα πρώτα 500 chars
