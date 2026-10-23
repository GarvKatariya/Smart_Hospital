# OCR Integration Documentation

The Smart Hospital Management System utilizes Optical Character Recognition (OCR) to extract text from medical documents, test reports, and prescriptions.

## Primary Engine: PaddleOCR
- **Why PaddleOCR**: Exceptional multi-lingual support, robust handling of skewed or low-quality scans, and accurate table extraction.
- **Supported Formats**: PNG, JPG, JPEG, PDF (converted to images first).

## Processing Pipeline
1. **Preprocessing**:
   - Image resizing and padding.
   - Contrast enhancement (Adaptive Histogram Equalization).
   - Binarization for noisy backgrounds.
2. **Detection & Recognition**:
   - Text boxes are detected and subsequently passed to the recognition model.
3. **Confidence Handling**:
   - Results below a `0.70` confidence threshold are flagged for manual review.
   - Entities extracted from low-confidence text are highlighted in the UI.

## Fallback Engine: Tesseract OCR
- If PaddleOCR fails to initialize or crashes on a specific image, the system falls back to `pytesseract`.
- Tesseract requires OS-level installation (`apt-get install tesseract-ocr` or `brew install tesseract`).

## Known Limitations
- Handwritten text recognition (especially doctor prescriptions) has high error rates.
- Severely faded thermal printed receipts may fail.
- Complex nested tables might lose structural formatting.
