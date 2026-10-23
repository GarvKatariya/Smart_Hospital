import os

project_root = "/Users/garvkatariya/.gemini/antigravity/scratch/smart-hospital-management-system"
os.chdir(project_root)

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

# Phase 5
write_file("models/bed_forecasting/__init__.py", "")
write_file("models/bed_forecasting/artifacts/.gitkeep", "")

write_file("models/bed_forecasting/preprocessing.py", """
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

def load_and_preprocess(data_path, window_size=30):
    df = pd.read_csv(data_path)
    # Assuming daily data, sum across departments if necessary, or just use as is
    # We will aggregate to total occupied_beds, admissions, discharges
    daily = df.groupby('date').agg({
        'admissions': 'sum',
        'discharges': 'sum',
        'occupied_beds': 'sum'
    }).reset_index()
    daily = daily.sort_values('date')
    
    features = daily[['admissions', 'discharges', 'occupied_beds']].values
    target = daily['occupied_beds'].values
    
    scaler = MinMaxScaler()
    scaled_features = scaler.fit_transform(features)
    
    X, y = [], []
    for i in range(len(scaled_features) - window_size - 7):
        X.append(scaled_features[i:i+window_size])
        y.append(target[i+window_size:i+window_size+7]) # 7 days ahead
        
    X = np.array(X)
    y = np.array(y)
    
    n = len(X)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)
    
    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]
    
    os.makedirs('models/bed_forecasting/artifacts', exist_ok=True)
    joblib.dump(scaler, 'models/bed_forecasting/artifacts/scaler.pkl')
    
    return X_train, y_train, X_val, y_val, X_test, y_test
""")

write_file("models/bed_forecasting/train.py", """
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import json
from .preprocessing import load_and_preprocess
import os

class BedForecastLSTM(nn.Module):
    def __init__(self, input_size=3, hidden_size=64, num_layers=2, output_size=7, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[:, -1, :])
        return out

def train_model():
    X_train, y_train, X_val, y_val, _, _ = load_and_preprocess('data/synthetic/beds/daily_occupancy.csv')
    
    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32))
    val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val, dtype=torch.float32))
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32)
    
    model = BedForecastLSTM()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    epochs = 100
    patience = 15
    best_loss = float('inf')
    patience_counter = 0
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            y_pred = model(X_batch)
            loss = criterion(y_pred, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                y_pred = model(X_batch)
                loss = criterion(y_pred, y_batch)
                val_loss += loss.item()
                
        val_loss /= len(val_loader)
        if val_loss < best_loss:
            best_loss = val_loss
            os.makedirs('models/bed_forecasting/artifacts', exist_ok=True)
            torch.save(model.state_dict(), 'models/bed_forecasting/artifacts/bed_lstm_v1.pt')
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                break

if __name__ == '__main__':
    train_model()
""")

write_file("models/bed_forecasting/evaluate.py", """
import torch
import json
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from .preprocessing import load_and_preprocess
from .train import BedForecastLSTM

def evaluate():
    _, _, _, _, X_test, y_test = load_and_preprocess('data/synthetic/beds/daily_occupancy.csv')
    model = BedForecastLSTM()
    model.load_state_dict(torch.load('models/bed_forecasting/artifacts/bed_lstm_v1.pt'))
    model.eval()
    
    with torch.no_grad():
        y_pred = model(torch.tensor(X_test, dtype=torch.float32)).numpy()
        
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # avoid division by zero
    y_test_safe = np.where(y_test == 0, 1e-9, y_test)
    mape = mean_absolute_percentage_error(y_test_safe, y_pred)
    
    metrics = {'mae': mae, 'rmse': rmse, 'mape': mape}
    with open('models/bed_forecasting/artifacts/metrics.json', 'w') as f:
        json.dump(metrics, f)

if __name__ == '__main__':
    evaluate()
""")

write_file("models/bed_forecasting/inference.py", """
import torch
import joblib
import numpy as np
from typing import List, Dict
import os
import sys

# Add models to path so we can import train
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from models.bed_forecasting.train import BedForecastLSTM

class BedForecastModel:
    def __init__(self, model_dir='models/bed_forecasting/artifacts'):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
    
    def load(self) -> bool:
        try:
            self.model = BedForecastLSTM()
            model_path = os.path.join(self.model_dir, 'bed_lstm_v1.pt')
            if not os.path.exists(model_path): return False
            self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            self.model.eval()
            
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            return True
        except Exception:
            return False
    
    def predict_next_day(self, recent_data: List[List[float]]) -> float:
        if not self.model or not self.scaler:
            return 0.0
        
        scaled_data = self.scaler.transform(recent_data)
        x = torch.tensor([scaled_data], dtype=torch.float32)
        with torch.no_grad():
            out = self.model(x).numpy()[0]
        return out[0]
    
    def predict_7day(self, recent_data: List[List[float]]) -> List[float]:
        if not self.model or not self.scaler:
            return [0.0]*7
            
        scaled_data = self.scaler.transform(recent_data)
        x = torch.tensor([scaled_data], dtype=torch.float32)
        with torch.no_grad():
            out = self.model(x).numpy()[0]
        return out.tolist()
""")

write_file("backend/app/services/bed_service.py", """
from typing import Dict, List
import datetime
from sqlalchemy.orm import Session
from models.bed_forecasting.inference import BedForecastModel

class BedService:
    def __init__(self):
        self.model = BedForecastModel()
        self._loaded = False
    
    def load_model(self):
        if not self._loaded:
            self._loaded = self.model.load()
            
    def get_current_status(self, db: Session) -> Dict:
        # Mocking for now, in reality fetch from DB
        return {
            'total_beds': 500,
            'occupied': 400,
            'available': 100,
            'occupancy_rate': 0.8,
            'by_department': {}
        }
    
    def get_forecast(self, recent_data=None) -> Dict:
        self.load_model()
        if not recent_data:
            # Mock data (30 days of [admissions, discharges, occupied_beds])
            recent_data = [[10, 8, 400] for _ in range(30)]
        
        forecast = self.model.predict_7day(recent_data) if self._loaded else [400]*7
        
        return {
            'dates': [(datetime.date.today() + datetime.timedelta(days=i)).isoformat() for i in range(1, 8)],
            'predicted_occupied': forecast,
            'predicted_available': [500 - x for x in forecast],
            'warnings': ['High occupancy expected' if x > 450 else 'Normal' for x in forecast]
        }
""")

write_file("backend/app/api/beds.py", """
from fastapi import APIRouter, Depends
from app.api.deps import get_db
from sqlalchemy.orm import Session
from app.services.bed_service import BedService

router = APIRouter()
bed_service = BedService()

@router.get("/status")
def get_bed_status(db: Session = Depends(get_db)):
    return bed_service.get_current_status(db)

@router.get("/forecast")
def get_bed_forecast():
    return bed_service.get_forecast()
""")

# Phase 6
write_file("models/appointment_recommendation/__init__.py", "")
write_file("models/appointment_recommendation/artifacts/.gitkeep", "")

write_file("models/appointment_recommendation/preprocessing.py", """
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib
import os

def load_and_preprocess(data_path):
    df = pd.read_csv(data_path)
    
    # Feature engineering
    df['department_encoded'] = LabelEncoder().fit_transform(df['department'])
    df['appointment_type_encoded'] = LabelEncoder().fit_transform(df['appointment_type'])
    df['urgency_encoded'] = df['urgency'].map({'low': 0, 'medium': 1, 'high': 2})
    
    df['day_of_week'] = pd.to_datetime(df['date']).dt.dayofweek
    df['hour'] = pd.to_datetime(df['time']).dt.hour
    
    # Target
    df['was_completed'] = (df['status'] == 'completed').astype(int)
    
    features = ['department_encoded', 'day_of_week', 'hour', 'appointment_type_encoded', 'urgency_encoded']
    
    X = df[features]
    y = df['was_completed']
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    os.makedirs('models/appointment_recommendation/artifacts', exist_ok=True)
    joblib.dump(scaler, 'models/appointment_recommendation/artifacts/scaler.pkl')
    
    from sklearn.model_selection import train_test_split
    X_train, X_temp, y_train, y_temp = train_test_split(X_scaled, y, test_size=0.3)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5)
    
    return X_train, y_train, X_val, y_val, X_test, y_test
""")

write_file("models/appointment_recommendation/train.py", """
import xgboost as xgb
import joblib
import os
from .preprocessing import load_and_preprocess

def train_model():
    X_train, y_train, X_val, y_val, _, _ = load_and_preprocess('data/synthetic/appointments/appointment_history.csv')
    
    model = xgb.XGBClassifier(max_depth=5, n_estimators=100, learning_rate=0.1)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], early_stopping_rounds=10, verbose=False)
    
    os.makedirs('models/appointment_recommendation/artifacts', exist_ok=True)
    joblib.dump(model, 'models/appointment_recommendation/artifacts/xgb_model.pkl')

if __name__ == '__main__':
    train_model()
""")

write_file("models/appointment_recommendation/evaluate.py", """
import joblib
import json
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from .preprocessing import load_and_preprocess

def evaluate():
    _, _, _, _, X_test, y_test = load_and_preprocess('data/synthetic/appointments/appointment_history.csv')
    
    model = joblib.load('models/appointment_recommendation/artifacts/xgb_model.pkl')
    y_pred = model.predict(X_test)
    
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred)
    }
    
    with open('models/appointment_recommendation/artifacts/metrics.json', 'w') as f:
        json.dump(metrics, f)

if __name__ == '__main__':
    evaluate()
""")

write_file("models/appointment_recommendation/inference.py", """
import joblib
from typing import List, Dict
import os

class AppointmentRecommender:
    def __init__(self, model_dir='models/appointment_recommendation/artifacts'):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
    
    def load(self) -> bool:
        try:
            self.model = joblib.load(os.path.join(self.model_dir, 'xgb_model.pkl'))
            self.scaler = joblib.load(os.path.join(self.model_dir, 'scaler.pkl'))
            return True
        except:
            return False
            
    def score_slots(self, candidate_slots: List[Dict]) -> List[Dict]:
        if not self.model or not candidate_slots: return candidate_slots
        
        # This assumes candidate slots have 'department_encoded', 'day_of_week', 'hour', 'appointment_type_encoded', 'urgency_encoded'
        features = [[s.get('department_encoded',0), s.get('day_of_week',0), s.get('hour',0), s.get('appointment_type_encoded',0), s.get('urgency_encoded',0)] for s in candidate_slots]
        scaled = self.scaler.transform(features)
        
        probs = self.model.predict_proba(scaled)[:, 1]
        
        for i, slot in enumerate(candidate_slots):
            slot['score'] = float(probs[i])
            slot['recommendation_reason'] = 'High likelihood of completion' if probs[i] > 0.7 else 'Standard slot'
            
        return sorted(candidate_slots, key=lambda x: x['score'], reverse=True)
""")

write_file("backend/app/services/appointment_service.py", """
from typing import List, Dict
from models.appointment_recommendation.inference import AppointmentRecommender
import datetime

class AppointmentService:
    def __init__(self):
        self.recommender = AppointmentRecommender()
        self._loaded = False
        
    def load_model(self):
        if not self._loaded:
            self._loaded = self.recommender.load()
            
    def get_recommendations(self, department_id, patient_id, urgency, db) -> List[Dict]:
        self.load_model()
        
        # Generate some dummy candidate slots
        candidates = []
        for i in range(1, 6):
            candidates.append({
                'slot_time': (datetime.datetime.now() + datetime.timedelta(days=i)).isoformat(),
                'department_encoded': 1,
                'day_of_week': i % 7,
                'hour': 10 + i,
                'appointment_type_encoded': 1,
                'urgency_encoded': 1 if urgency == 'medium' else 0,
                'doctor_id': 1
            })
            
        if self._loaded:
            return self.recommender.score_slots(candidates)[:5]
        return candidates[:5]
        
    def create_appointment(self, data, patient_id, db) -> Dict:
        return {"status": "success", "appointment": data}
        
    def get_appointments(self, user_id, role, db) -> List[Dict]:
        return []
""")

write_file("backend/app/api/appointments.py", """
from fastapi import APIRouter, Depends
from typing import Dict, List
from app.api.deps import get_db
from sqlalchemy.orm import Session
from app.services.appointment_service import AppointmentService

router = APIRouter()
appointment_service = AppointmentService()

@router.get("/recommendations")
def get_recommendations(department_id: int, patient_id: int, urgency: str, db: Session = Depends(get_db)):
    return appointment_service.get_recommendations(department_id, patient_id, urgency, db)

@router.post("/")
def create_appointment(data: Dict, patient_id: int = 1, db: Session = Depends(get_db)):
    return appointment_service.create_appointment(data, patient_id, db)

@router.get("/")
def list_appointments(user_id: int = 1, role: str = "patient", db: Session = Depends(get_db)):
    return appointment_service.get_appointments(user_id, role, db)
""")


# Phase 7
write_file("ocr/__init__.py", "")

write_file("ocr/preprocess.py", """
from PIL import Image, ImageEnhance, ImageFilter
import io

def preprocess_image(image_bytes: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    img = img.filter(ImageFilter.SHARPEN)
    return img
""")

write_file("ocr/paddleocr_service.py", """
from typing import Dict, List, Tuple
import os
import logging

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.engine = None
        self.engine_type = None
        self._initialize()
    
    def _initialize(self):
        try:
            from paddleocr import PaddleOCR
            self.engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            self.engine_type = 'paddleocr'
            logger.info('PaddleOCR initialized')
            return
        except ImportError:
            pass
        except Exception:
            pass
            
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.engine_type = 'tesseract'
            logger.info('Using Tesseract OCR fallback')
            return
        except Exception:
            pass
            
        self.engine_type = 'mock'
        logger.warning('No OCR engine available, using mock OCR')
    
    def extract_text(self, image_path: str) -> Dict:
        if self.engine_type == 'paddleocr':
            return self._paddle_extract(image_path)
        elif self.engine_type == 'tesseract':
            return self._tesseract_extract(image_path)
        else:
            return self._mock_extract(image_path)
            
    def _paddle_extract(self, image_path) -> Dict:
        result = self.engine.ocr(image_path, cls=True)
        lines = []
        total_confidence = 0
        count = 0
        for page in result:
            if page:
                for line in page:
                    text = line[1][0]
                    confidence = line[1][1]
                    lines.append({'text': text, 'confidence': confidence, 'bbox': line[0]})
                    total_confidence += confidence
                    count += 1
                    
        full_text = '\\n'.join([l['text'] for l in lines])
        avg_confidence = total_confidence / count if count > 0 else 0
        
        return {
            'full_text': full_text,
            'lines': lines,
            'average_confidence': avg_confidence,
            'engine': 'paddleocr',
            'page_count': len(result) if result else 0
        }

    def _tesseract_extract(self, image_path) -> Dict:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        lines = []
        for i, word in enumerate(data['text']):
            if word.strip():
                conf = float(data['conf'][i]) / 100
                lines.append({'text': word, 'confidence': conf})
                
        avg_conf = sum(l['confidence'] for l in lines) / len(lines) if lines else 0
        
        return {
            'full_text': text,
            'lines': lines,
            'average_confidence': avg_conf,
            'engine': 'tesseract'
        }
        
    def _mock_extract(self, image_path) -> Dict:
        return {
            'full_text': '[Mock OCR] This is placeholder text extracted from the image. Install PaddleOCR or Tesseract for real OCR.',
            'lines': [{'text': '[Mock OCR] Placeholder text', 'confidence': 0.5}],
            'average_confidence': 0.5,
            'engine': 'mock',
            'note': 'No OCR engine available. Install paddleocr or pytesseract.'
        }

ocr_service = OCRService()
""")

write_file("ocr/report_parser.py", """
from typing import Dict

def parse_medical_report(text: str) -> Dict:
    return {
        "summary": "Parsed report summary.",
        "sections": {"raw": text}
    }
""")

write_file("ocr/prescription_parser.py", """
from typing import Dict, List

def parse_prescription(text: str) -> List[Dict]:
    return [
        {"medication": "Sample Med", "dosage": "10mg", "frequency": "daily"}
    ]
""")

write_file("backend/app/services/report_service.py", """
from typing import Dict
from ocr.paddleocr_service import ocr_service
from ocr.report_parser import parse_medical_report
import tempfile

class ReportService:
    def process_report_image(self, image_bytes: bytes) -> Dict:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            tmp_path = f.name
            
        ocr_result = ocr_service.extract_text(tmp_path)
        parsed = parse_medical_report(ocr_result['full_text'])
        
        import os
        os.remove(tmp_path)
        
        return {
            "ocr": ocr_result,
            "parsed": parsed
        }
""")

write_file("backend/app/api/reports.py", """
from fastapi import APIRouter, UploadFile, File
from app.services.report_service import ReportService

router = APIRouter()
report_service = ReportService()

@router.post("/upload")
async def upload_report(file: UploadFile = File(...)):
    contents = await file.read()
    return report_service.process_report_image(contents)
""")

write_file("data/sample_documents/medical_reports/README.md", "# Sample Medical Reports\nPlace medical report images here for testing OCR.")
write_file("data/sample_documents/prescriptions/README.md", "# Sample Prescriptions\nPlace prescription images here for testing OCR.")

print("Generation complete")
