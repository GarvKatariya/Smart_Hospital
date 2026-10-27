'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { symptomAPI } from '@/lib/api';
import { Stethoscope, CheckCircle } from 'lucide-react';

interface SymptomResult {
  predicted_condition: string;
  confidence: number;
  department: string;
  explanation: string;
}

export default function SymptomCheckerPage() {
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SymptomResult | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    symptomAPI.list().then(res => setSymptoms(res.data?.symptoms || [])).catch(console.error);
  }, []);

  const toggleSymptom = (s: string) => {
    setSelectedSymptoms(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await symptomAPI.check({ symptoms_text: description, selected_symptoms: selectedSymptoms });
      setResult(res.data);
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setError(typeof detail === 'string' ? detail : 'Could not analyze these symptoms.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">AI Symptom Checker</h2>
        <p className="text-muted-foreground">Describe your symptoms for an initial AI assessment.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Describe Symptoms</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && <Alert variant="error">{error}</Alert>}
            <div>
              <label className="text-sm font-medium">How are you feeling?</label>
              <textarea
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:text-sm"
                rows={4}
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="E.g., I have a severe headache and fever since yesterday..."
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Common Symptoms</label>
              <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto p-2 border rounded-md">
                {symptoms.map(s => (
                  <button
                    key={s}
                    onClick={() => toggleSymptom(s)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      selectedSymptoms.includes(s) ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {s.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>

            <Button className="w-full" onClick={handleSubmit} isLoading={loading} disabled={!description && selectedSymptoms.length === 0}>
              <Stethoscope className="mr-2 h-4 w-4" /> Analyze Symptoms
            </Button>
          </CardContent>
        </Card>

        {result && (
          <Card className="bg-blue-50/50">
            <CardHeader>
              <CardTitle className="flex items-center">
                <CheckCircle className="text-green-500 mr-2" /> Assessment Result
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-white rounded-lg border">
                <h3 className="text-lg font-semibold text-gray-900">Predicted Condition</h3>
                <p className="text-2xl font-bold text-blue-700 capitalize mt-1">{(result.predicted_condition || '').replace(/_/g, ' ')}</p>
                <div className="mt-2 flex items-center justify-between text-sm text-gray-500">
                  <span>Confidence Score</span>
                  <span>{((result.confidence || 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                  <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${(result.confidence || 0) * 100}%` }}></div>
                </div>
              </div>

              {result.department && (
                <div>
                  <p className="text-sm font-medium">Recommended Department:</p>
                  <Badge variant="info" className="mt-1 text-sm px-3 py-1">{result.department}</Badge>
                </div>
              )}

              {result.explanation && (
                <div className="p-4 bg-white rounded-lg border text-sm text-gray-700">
                  <p className="font-semibold mb-1">AI Explanation:</p>
                  <p>{result.explanation}</p>
                </div>
              )}

              <Alert variant="warning" className="text-xs">
                This is an AI assessment and does not constitute medical advice. Please consult a doctor for a proper diagnosis.
              </Alert>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
