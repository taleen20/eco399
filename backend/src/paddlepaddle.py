from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import io
import gc
import fitz
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from paddleocr import PaddleOCR
from transformers import pipeline
from typing import List, Tuple
import json
from werkzeug.utils import secure_filename
import tempfile
import shutil

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize models (load once at startup)
print("Loading OCR model...")
ocr = PaddleOCR(use_angle_cls=True, lang='en')
print("Loading table detection model...")
table_detector = pipeline("object-detection", model="TahaDouaji/detr-doc-table-detection")
print("Models loaded successfully!")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def pdf_to_images(pdf_path: str, batch_size: int = 5, dpi: int = 300) -> List[Image.Image]:
    """Convert PDF to images"""
    doc = fitz.open(pdf_path)
    images = []
    
    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            mat = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            images.append(image)
            
            pix = None
            page = None
        except Exception as e:
            print(f"Error processing page {page_num+1}: {e}")
            continue
    
    doc.close()
    gc.collect()
    return images


def preprocess_image_for_ocr(
    image: Image.Image,
    denoise_strength: int = 7,
    clahe_clip: float = 2.0,
    clahe_tile: Tuple[int, int] = (8, 8),
    sharpen_amount: float = 0.8
) -> Image.Image:
    """Apply preprocessing to boost OCR accuracy"""
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    
    # Denoise
    if denoise_strength > 0:
        gray = cv2.fastNlMeansDenoising(gray, None, h=denoise_strength, 
                                       templateWindowSize=7, searchWindowSize=21)
    
    # Local contrast
    gray = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=clahe_tile).apply(gray)
    
    # Sharpen
    if sharpen_amount > 0:
        blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
        gray = cv2.addWeighted(gray, 1 + sharpen_amount, blurred, -sharpen_amount, 0)
    
    # Binarization
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 35, 10)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary = cv2.bitwise_or(thr, otsu)
    
    return Image.fromarray(binary)


def detect_and_crop_tables(image: Image.Image, score_thresh: float = 0.5, pad: int = 6) -> List[Image.Image]:
    """Detect tables and crop them from image"""
    w, h = image.size
    preds = table_detector(images=image)
    
    table_preds = [
        p for p in preds
        if p.get("label", "").lower() == "table" and p.get("score", 0) >= score_thresh
    ]
    
    crops = []
    for p in table_preds:
        xmin = max(0, int(p["box"]["xmin"]) - pad)
        ymin = max(0, int(p["box"]["ymin"]) - pad)
        xmax = min(w, int(p["box"]["xmax"]) + pad)
        ymax = min(h, int(p["box"]["ymax"]) + pad)
        crops.append(image.crop((xmin, ymin, xmax, ymax)))
    
    return crops


def ocr_to_csv(ocr_results: List) -> str:
    """Convert OCR results to CSV format"""
    csv_lines = []
    
    for page_idx, page_result in enumerate(ocr_results):
        if not page_result:
            continue
            
        # Group text by rows based on y-coordinates
        texts_with_coords = []
        for line in page_result:
            if len(line) >= 2:
                bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text = line[1][0] if isinstance(line[1], tuple) else line[1]
                
                # Get average y-coordinate for row grouping
                y_avg = sum(point[1] for point in bbox) / 4
                x_avg = sum(point[0] for point in bbox) / 4
                
                texts_with_coords.append((y_avg, x_avg, text))
        
        # Sort by y then x
        texts_with_coords.sort(key=lambda t: (round(t[0] / 20), t[1]))
        
        # Group into rows
        current_row = []
        current_y = None
        y_threshold = 20
        
        for y, x, text in texts_with_coords:
            if current_y is None or abs(y - current_y) < y_threshold:
                current_row.append(text)
                current_y = y if current_y is None else current_y
            else:
                if current_row:
                    csv_lines.append(','.join(f'"{cell}"' for cell in current_row))
                current_row = [text]
                current_y = y
        
        if current_row:
            csv_lines.append(','.join(f'"{cell}"' for cell in current_row))
    
    return '\n'.join(csv_lines)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)