# AI feature test files and checks

All medical documents in this folder are fictional test data. Do not use them as medical records or for care decisions.

## Chatbot

The chatbot retrieves from the project's existing demo knowledge base in `rag/documents/`. These files are synthetic hospital policy and should not be mistaken for real hospital information:

- `rag/documents/visiting_hours.md`
- `rag/documents/appointments.md`
- `rag/documents/departments.md`
- `rag/documents/faq.md`

Try these questions in the chatbot and check that the reply cites the indicated source:

| Question | Expected fact | Expected source |
| --- | --- | --- |
| What are the ICU/CCU visiting hours, and how many visitors are allowed? | 11:00–11:30 AM and 5:00–5:30 PM; one family member | `visiting_hours.md` |
| How far in advance can an appointment be rescheduled? | Up to 12 hours before | `appointments.md` |
| Is there a cafeteria, and where is it? | Yes, 24/7, on the ground floor | `faq.md` |

I ran the first two questions through the chatbot service. Both returned the expected facts and included the matching source file in retrieval results.

## Prescription OCR

Upload [`prescriptions/sample_prescription.png`](prescriptions/sample_prescription.png). It is a fictional printed prescription copied from the project's existing sample image. Its visible medicines are Amoxicillin, Paracetamol, Omeprazole, and cough linctus.

**Observed check:** the current OCR engine is `mock`. The service ignored the image and returned fixed CBC text; the prescription parser then labeled Hemoglobin and Glucose as medicines. This flow is not currently reading or extracting the prescription correctly.

## Medical-report OCR

Upload any of these image files to the report flow:

- [`medical_reports/local_sample_report.png`](medical_reports/local_sample_report.png): the project's fictional CBC/lipid report image.
- [`medical_reports/synthetic_lab_report_clean.png`](medical_reports/synthetic_lab_report_clean.png): clean public synthetic lab report.
- [`medical_reports/synthetic_lab_report_scanned.png`](medical_reports/synthetic_lab_report_scanned.png): degraded scan of the same report.

The corresponding PDFs and ground-truth JSON are in this folder. The public report is created by Synthesized, identifies itself as synthetic, and is offered under CC BY 4.0; retain attribution if redistributing it. Source: <https://www.synthesized.io/sample-lab-report>.

**Observed check:** all three images returned exactly the same fixed demo CBC text from mock OCR. The report parser therefore did not extract the values shown in these uploaded images.

## What a passing OCR check looks like

The returned OCR text should change when the image changes and should match the visible medicine names or lab values. Compare the report output against `medical_reports/synthetic_lab_report_ground_truth.json`. The current mock-engine result fails this check, even though the downstream parser returns structured fields.
