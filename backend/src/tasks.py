import os
import shutil
import tempfile

from celery_app import celery
from paddlepaddle import (
    ocr, pdf_to_images, preprocess_image_for_ocr,
    detect_and_crop_tables, ocr_to_csv, OUTPUT_FOLDER,
)


@celery.task(bind=True)
def process_pdf(self, pdf_path: str, language: str) -> dict:
    temp_dir = None
    try:
        self.update_state(state='PROGRESS', meta={'step': 'Converting PDF to images'})
        images = pdf_to_images(pdf_path)

        self.update_state(state='PROGRESS', meta={'step': 'Preprocessing images'})
        processed_images = [preprocess_image_for_ocr(img) for img in images]

        self.update_state(state='PROGRESS', meta={'step': 'Detecting tables'})
        all_table_crops = []
        for img in processed_images:
            all_table_crops.extend(detect_and_crop_tables(img))

        self.update_state(
            state='PROGRESS',
            meta={'step': f'Running OCR on {len(all_table_crops)} table(s)'}
        )
        temp_dir = tempfile.mkdtemp()
        all_ocr_results = []
        for crop in all_table_crops:
            temp_img_path = os.path.join(temp_dir, 'temp_table.png')
            crop.save(temp_img_path)
            result = ocr.ocr(temp_img_path, cls=True)
            if result and result[0]:
                all_ocr_results.append(result[0])

        self.update_state(state='PROGRESS', meta={'step': 'Saving CSV'})
        csv_content = ocr_to_csv(all_ocr_results)

        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        csv_filename = f"{base_name}.csv"
        csv_path = os.path.join(OUTPUT_FOLDER, csv_filename)
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        os.remove(pdf_path)

        return {'filename': csv_filename, 'tables_found': len(all_table_crops)}

    except Exception:
        raise
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
