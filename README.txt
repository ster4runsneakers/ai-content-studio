AI Content Studio — Image Pipeline Plus
============================================

Features:
- Aspect selection (1:1, 9:16, 4:5, 16:9)
- JPEG quality option
- URL & base64 handling for OpenAI gpt-image-1
- Resize & watermark pipeline
- Retries for transient errors
- Metadata JSON saved next to image

.env:
OPENAI_API_KEY=sk-...

Run:
pip install flask pillow openai python-dotenv requests
python app.py
