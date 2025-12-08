from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/upload", methods=["POST"])
def upload_pdf():
    # Check if a file was sent
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    pdf_file = request.files["file"]
    if pdf_file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Get the language parameter
    language = request.form.get("language") or request.args.get("language")
    if not language:
        return jsonify({"error": "Missing 'language' parameter"}), 400

    # For now, just confirm what we received
    return jsonify({
        "filename": pdf_file.filename,
        "language": language,
        "message": "PDF received successfully"
    }), 200


@app.route('/upload', methods=['POST'])
def upload_file():
    """Main endpoint to handle PDF upload and conversion"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    language = request.form.get('language', 'en')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        # Create temp directory for processing
        temp_dir = tempfile.mkdtemp()
        
        # Process PDF
        print("Converting PDF to images...")
        images = pdf_to_images(pdf_path)
        
        print("Preprocessing images...")
        processed_images = [preprocess_image_for_ocr(img) for img in images]
        
        print("Detecting tables...")
        all_table_crops = []
        for img in processed_images:
            crops = detect_and_crop_tables(img)
            all_table_crops.extend(crops)
        
        print(f"Found {len(all_table_crops)} tables")
        
        # Run OCR on all table crops
        print("Running OCR...")
        all_ocr_results = []
        for crop in all_table_crops:
            # Save crop to temp file for OCR
            temp_img_path = os.path.join(temp_dir, 'temp_table.png')
            crop.save(temp_img_path)
            result = ocr.ocr(temp_img_path, cls=True)
            if result and result[0]:
                all_ocr_results.append(result[0])
        
        # Convert to CSV
        print("Converting to CSV...")
        csv_content = ocr_to_csv(all_ocr_results)
        
        # Save CSV
        csv_filename = f"{os.path.splitext(filename)[0]}.csv"
        csv_path = os.path.join(OUTPUT_FOLDER, csv_filename)
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # Cleanup
        os.remove(pdf_path)
        shutil.rmtree(temp_dir)
        
        return jsonify({
            'success': True,
            'filename': csv_filename,
            'tables_found': len(all_table_crops),
            'csv_path': csv_path,
            'message': 'File processed successfully'
        })
    
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download the generated CSV file"""
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})


if __name__ == "__main__":
    app.run(debug=True)
