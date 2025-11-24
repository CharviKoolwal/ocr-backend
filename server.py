import io
import base64
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import easyocr
import re

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load EasyOCR reader ONCE
reader = easyocr.Reader(['en'])


# ---------------------
# IMAGE PREPROCESSING
# ---------------------
def preprocess_pil(pil_img):
    """Convert PIL image → OpenCV and preprocess."""
    img = np.array(pil_img)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return img


# ---------------------
# TEXT EXTRACTION HELPERS
# ---------------------
def extract_date(text):
    date_pattern = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    match = re.search(date_pattern, text)
    return match.group(1) if match else None


def extract_total(text):
    total_pattern = r"(?:TOTAL|AMOUNT DUE)[^\d]*(\d+\.\d{2})"
    match = re.search(total_pattern, text, re.IGNORECASE)
    return match.group(1) if match else None


# ---------------------
# UPLOAD ENDPOINT
# ---------------------
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Handle receipt upload and OCR."""
    raw = await file.read()

    # Load image
    pil = Image.open(io.BytesIO(raw)).convert("RGB")

    # Preprocess
    processed = preprocess_pil(pil)

    # Run OCR
    text_list = reader.readtext(processed, detail=0)
    text = "\n".join(text_list)

    # Extract fields
    date = extract_date(text)
    total = extract_total(text)

    # Encode processed image
    _, buff = cv2.imencode(".png", processed)
    processed_b64 = (
        "data:image/png;base64," + base64.b64encode(buff).decode()
    )

    return {
        "filename": file.filename,
        "raw_text": text,
        "date": date,
        "total": total,
        "processed_image": processed_b64
    }
