'use client';

import React, { useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Alert } from '@/components/ui/Alert';
import { diseaseAPI, DiseasePredictionInput } from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertTriangle, Activity } from 'lucide-react';

interface DiseaseResult {
  prediction: number;
  probability: number;
  risk_category: string;
  feature_importance: Record<string, number>;
  disclaimer: string;
}

export default function DiseasePredictionPage() {
  const [formData, setFormData] = useState({
    age: '', sex: '1', cp: '0', trestbps: '', chol: '', fbs: '0',
    restecg: '0', thalach: '', exang: '0', oldpeak: '', slope: '0', ca: '0', thal: '2'
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiseaseResult | null>(null);
  const [error, setError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const payload: DiseasePredictionInput = {
        age: Number(formData.age), sex: Number(formData.sex), cp: Number(formData.cp),
        trestbps: Number(formData.trestbps), chol: Number(formData.chol), fbs: Number(formData.fbs),
        restecg: Number(formData.restecg), thalach: Number(formData.thalach), exang: Number(formData.exang),
        oldpeak: Number(formData.oldpeak), slope: Number(formData.slope), ca: Number(formData.ca), thal: Number(formData.thal),
      };
      const res = await diseaseAPI.predict(payload);
      setResult(res.data);
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setError(typeof detail === 'string' ? detail : 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  const importanceData = result?.feature_importance
    ? Object.entries(result.feature_importance).map(([key, value]) => ({ name: key, value }))
    : [];

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Heart Disease Risk Prediction</h2>
        <p className="text-muted-foreground">AI-powered analysis of cardiovascular parameters.</p>
      </div>

      <Alert variant="warning" title="Disclaimer">
        This is an AI prediction tool and is not a substitute for professional medical advice, diagnosis, or treatment.
      </Alert>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Patient Parameters</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && <Alert variant="error">{error}</Alert>}
              <div className="grid grid-cols-2 gap-4">
                <Input label="Age" type="number" name="age" value={formData.age} onChange={handleChange} required />
                <div>
                  <label className="text-sm font-medium">Sex</label>
                  <select name="sex" value={formData.sex} onChange={handleChange} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm mt-1">
                    <option value="1">Male</option><option value="0">Female</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Chest Pain Type (0-3)</label>
                  <select name="cp" value={formData.cp} onChange={handleChange} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm mt-1">
                    <option value="0">Typical Angina (0)</option><option value="1">Atypical Angina (1)</option>
                    <option value="2">Non-anginal Pain (2)</option><option value="3">Asymptomatic (3)</option>
                  </select>
                </div>
                <Input label="Resting Blood Pressure (mm Hg)" type="number" name="trestbps" value={formData.trestbps} onChange={handleChange} required />
                <Input label="Cholesterol (mg/dl)" type="number" name="chol" value={formData.chol} onChange={handleChange} required />
                <div>
                  <label className="text-sm font-medium">Fasting Blood Sugar &gt; 120 mg/dl</label>
                  <select name="fbs" value={formData.fbs} onChange={handleChange} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm mt-1">
                    <option value="1">Yes (1)</option><option value="0">No (0)</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Resting ECG (0-2)</label>
                  <select name="restecg" value={formData.restecg} onChange={handleChange} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm mt-1">
                    <option value="0">Normal (0)</option><option value="1">ST-T Wave Abnormality (1)</option><option value="2">LV Hypertrophy (2)</option>
                  </select>
                </div>
                <Input label="Max Heart Rate" type="number" name="thalach" value={formData.thalach} onChange={handleChange} required />
                <div>
                  <label className="text-sm font-medium">Exercise Induced Angina</label>
                  <select name="exang" value={formData.exang} onChange={handleChange} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm mt-1">
                    <option value="1">Yes (1)</option><option value="0">No (0)</option>
                  </select>
                </div>
                <Input label="ST Depression" type="number" step="0.1" name="oldpeak" value={formData.oldpeak} onChange={handleChange} required />
                <div>
                  <label className="text-sm font-medium">Slope of Peak Exercise ST (0-2)</label>
                  <select name="slope" value={formData.slope} onChange={handleChange} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm mt-1">
                    <option value="0">Upsloping (0)</option><option value="1">Flat (1)</option><option value="2">Downsloping (2)</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Number of Major Vessels (0-3)</label>
                  <select name="ca" value={formData.ca} onChange={handleChange} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm mt-1">
                    <option value="0">0</option><option value="1">1</option><option value="2">2</option><option value="3">3</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Thalassemia (0-3)</label>
                  <select name="thal" value={formData.thal} onChange={handleChange} className="flex h-10 w-full rounded-md border px-3 py-2 text-sm mt-1">
                    <option value="0">0</option><option value="1">Normal (1)</option><option value="2">Fixed Defect (2)</option><option value="3">Reversable Defect (3)</option>
                  </select>
                </div>
              </div>
              <Button type="submit" isLoading={loading} className="w-full mt-4">Predict Risk</Button>
            </form>
          </CardContent>
        </Card>

        {result && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Prediction Results</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col items-center justify-center space-y-4 py-8">
                <div className={`p-6 rounded-full ${result.prediction === 1 ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}>
                  {result.prediction === 1 ? <AlertTriangle size={48} /> : <Activity size={48} />}
                </div>
                <h3 className="text-2xl font-bold">{result.prediction === 1 ? 'High Risk' : 'Low Risk'}</h3>
                <p className="text-lg">Probability: <span className="font-semibold">{(result.probability * 100).toFixed(1)}%</span></p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Feature Importance</CardTitle>
              </CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={importanceData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <XAxis type="number" />
                    <YAxis dataKey="name" type="category" width={80} textAnchor="end" tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
