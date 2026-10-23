from .provider import LLMProvider
from app.core.logging import get_logger

logger = get_logger(__name__)

class MockLLMProvider(LLMProvider):
    """Mock LLM provider for demo mode when no API key is available."""
    
    def generate(self, prompt, context=None):
        # Generate sensible mock responses based on prompt content
        if 'symptom' in prompt.lower():
            return self._symptom_response(context)
        elif 'report' in prompt.lower() or 'summary' in prompt.lower():
            return self._report_response(context)
        elif 'prescription' in prompt.lower():
            return self._prescription_response(context)
        else:
            return self._general_response(context)
    
    def _symptom_response(self, context):
        disease = context.get('predicted_condition', 'Unknown') if context else 'Unknown'
        confidence = context.get('confidence', 0) if context else 0
        department = context.get('department', 'General Medicine') if context else 'General Medicine'
        return f"""Based on the symptoms you've described, the AI screening system suggests a possible association with {disease} (confidence: {confidence:.0%}).

**What this means:** This condition affects many people and can range from mild to moderate in severity. The symptoms you've reported are commonly associated with this condition.

**Recommended Department:** {department}

**What you should do:**
1. Schedule an appointment with a {department} specialist
2. Keep track of your symptoms and any changes
3. Stay hydrated and rest adequately
4. Bring a list of all medications you're currently taking

⚠️ **Important Disclaimer:** This is an AI-assisted screening tool and NOT a medical diagnosis. The prediction is based on pattern matching with reported symptoms. Please consult a qualified healthcare professional for proper medical evaluation and diagnosis. Seek immediate medical attention if you experience severe symptoms."""
    
    def _report_response(self, context):
        return """**Report Summary (Demo Mode)**

This is a demo summary generated without an LLM API key.

**Key Observations:**
- The report has been processed through OCR
- Values have been extracted and categorized
- A real summary would provide detailed medical interpretation

**To enable full AI summaries:**
Set the GEMINI_API_KEY environment variable with a valid Google Gemini API key.

⚠️ **Disclaimer:** AI-generated summaries are for informational purposes only. Always consult your doctor for medical interpretation."""
    
    def _prescription_response(self, context):
        return """**Prescription Explanation (Demo Mode)**

The medications listed have been extracted from the uploaded prescription image.

Please verify all medication names and dosages with your pharmacist, especially for items marked with low confidence scores.

⚠️ **Disclaimer:** Never change your medication regimen based on AI analysis alone. Always follow your doctor's instructions."""
    
    def _general_response(self, context):
        return "This is a demo response. Set GEMINI_API_KEY for full AI capabilities."
    
    def is_available(self):
        return True  # Always available as fallback
