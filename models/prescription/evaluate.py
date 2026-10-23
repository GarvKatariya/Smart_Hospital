"""
Prescription Understanding - Evaluation
Evaluates rule-based NER on a set of test cases.
"""
import json
import os
from train import PrescriptionNER

def evaluate_model():
    test_cases = [
        {
            "text": "Paracetamol 500mg - Twice daily for 5 days",
            "expected": {"name": "Paracetamol (Acetaminophen)", "dosage": "500mg", "route": "Oral"}
        },
        {
            "text": "Amoxicillin 250mg capsule - Three times daily for 7 days",
            "expected": {"name": "Amoxicillin", "dosage": "250mg", "route": "Oral"}
        },
        {
            "text": "Apply Diclofenac 10g Topical gel twice a day",
            "expected": {"name": "Diclofenac", "dosage": "10g", "route": "Topical"}
        },
        {
            "text": "UnknownMed 10mg once daily",
            "expected": {"name": "UnknownMed", "dosage": "10mg", "route": "Oral"}
        }
    ]
    
    ner = PrescriptionNER()
    
    correct = 0
    total_expected = len(test_cases)
    extracted_total = 0
    
    print("Starting evaluation...")
    for case in test_cases:
        results = ner.extract_medications(case['text'])
        extracted_total += len(results)
        
        if results:
            r = results[0]
            if (r.get('normalized_name') == case['expected']['name'] and 
                r.get('dosage') == case['expected']['dosage'] and 
                r.get('route') == case['expected']['route']):
                correct += 1
    
    precision = correct / extracted_total if extracted_total > 0 else 0
    recall = correct / total_expected if total_expected > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    report = {
        "test_cases": total_expected,
        "extracted": extracted_total,
        "correct": correct,
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1)
    }
    
    print(json.dumps(report, indent=2))
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'artifacts')
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'evaluation_metrics.json'), 'w') as f:
        json.dump(report, f, indent=2)

if __name__ == '__main__':
    evaluate_model()
