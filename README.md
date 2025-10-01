📄 README.md
# 🎨 AI Content Studio

## 🇬🇷 Περιγραφή (Greek)

Το **AI Content Studio** είναι μια εφαρμογή Flask που σου επιτρέπει να δημιουργείς:
- 📷 Εικόνες με OpenAI DALL·E 3
- 🖼️ Λογότυπα με διαφανές φόντο
- 💾 Αποθήκευση σε τοπικό δίσκο ή/και στο **Cloudinary**
- 🌗 Theme Switcher (Light / Dark / Auto)
- 📜 Καταγραφή ενεργειών (logs) και δυνατότητα **backup ZIP**

### 🚀 Τοπική Εκτέλεση (Local)

1. Κλωνοποίησε το repo:
   ```bash
   git clone https://github.com/ster4runsneakers/ai-content-studio.git
   cd ai-content-studio


Δημιούργησε virtual environment:

python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Linux / Mac


Εγκατάστησε εξαρτήσεις:

pip install -r requirements.txt


Φτιάξε αρχείο .env:

OPENAI_API_KEY=sk-xxxxxx
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
CLOUDINARY_FOLDER=ai-content-studio


Τρέξε την εφαρμογή:

python app.py


Η εφαρμογή ανοίγει στο: http://127.0.0.1:5000

🌐 Deploy στο Render

Push στο GitHub (main branch).

Στο Render → New Web Service → διάλεξε το repo.

Ρύθμιση:

Build command: pip install -r requirements.txt

Start command: gunicorn app:app

Πρόσθεσε Environment Variables:

OPENAI_API_KEY

CLOUDINARY_URL

CLOUDINARY_FOLDER

Η εφαρμογή θα ανέβει και θα είναι live 🎉

🇬🇧 Description (English)

AI Content Studio is a Flask application that allows you to:

📷 Generate images with OpenAI DALL·E 3

🖼️ Create logos with transparent background

💾 Save to local disk and/or Cloudinary

🌗 Theme Switcher (Light / Dark / Auto)

📜 Action logs and ZIP backup support

🚀 Run Locally

Clone the repo:

git clone https://github.com/ster4runsneakers/ai-content-studio.git
cd ai-content-studio


Create virtual environment:

python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Linux / Mac


Install dependencies:

pip install -r requirements.txt


Create .env file:

OPENAI_API_KEY=sk-xxxxxx
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
CLOUDINARY_FOLDER=ai-content-studio


Run the app:

python app.py


App runs at: http://127.0.0.1:5000

🌐 Deploy on Render

Push to GitHub (main branch).

On Render → New Web Service → select repo.

Setup:

Build command: pip install -r requirements.txt

Start command: gunicorn app:app

Add Environment Variables:

OPENAI_API_KEY

CLOUDINARY_URL

CLOUDINARY_FOLDER

The app will deploy and go live 🎉

📌 Σημειώσεις / Notes

Τα local αρχεία σώζονται σε static/outputs/ (αλλά στο Render είναι προσωρινά).

Για μόνιμη αποθήκευση → Cloudinary.

Τα logs γράφονται σε data/logs.jsonl.

Μπορείς να κατεβάσεις όλα τα τοπικά αρχεία από το route /backup.