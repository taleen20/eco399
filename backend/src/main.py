import os
import uuid

from celery.result import AsyncResult
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from celery_app import celery
from paddlepaddle import UPLOAD_FOLDER, OUTPUT_FOLDER, MAX_FILE_SIZE, allowed_file
from tasks import process_pdf

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    language = request.form.get('language', 'en')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(pdf_path)

    task = process_pdf.delay(pdf_path, language)
    return jsonify({'job_id': task.id}), 202


@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    result = AsyncResult(job_id, app=celery)
    state = result.state

    if state == 'PENDING':
        return jsonify({'state': 'pending', 'step': 'Queued'})
    elif state == 'STARTED':
        return jsonify({'state': 'started', 'step': 'Starting'})
    elif state == 'PROGRESS':
        return jsonify({'state': 'progress', 'step': result.info.get('step', '')})
    elif state == 'SUCCESS':
        return jsonify({'state': 'success', **result.result})
    elif state == 'FAILURE':
        return jsonify({'state': 'failure', 'error': str(result.info)})
    else:
        return jsonify({'state': state.lower()})


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
