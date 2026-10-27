'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { prescriptionAPI } from '@/lib/api';
import { Upload, Pill, CheckCircle, AlertCircle, AlertTriangle, FileText } from 'lucide-react';
import api from '@/lib/api';

type WritingMode = 'printed' | 'handwritten';

export default function PrescriptionsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [writingMode, setWritingMode] = useState<WritingMode>('printed');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    setResult(null);
    setError('');
    if (f && f.type.startsWith('image/')) {
      const url = URL.createObjectURL(f);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('writing_mode', writingMode);
      const res = await api.post('/api/prescriptions/analyze', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data.analysis);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to analyze prescription. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const medications: any[] = result?.medications ?? [];
  const reviewCount = medications.filter((m: any) => m.requires_review).length;

  const confidenceBadge = (conf: number) => {
    if (conf >= 0.85) return <Badge variant="success">{Math.round(conf * 100)}%</Badge>;
    if (conf >= 0.65) return <Badge variant="warning">{Math.round(conf * 100)}%</Badge>;
    return <Badge variant="danger">{Math.round(conf * 100)}% ⚠</Badge>;
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Prescription Analyzer</h2>
        <p className="text-muted-foreground">Digitize prescriptions using AI-powered OCR. All results require verification against the original document.</p>
      </div>

      {/* Mode selector */}
      <div className="flex gap-3">
        {(['printed', 'handwritten'] as const).map(mode => (
          <button
            key={mode}
            onClick={() => setWritingMode(mode)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
              writingMode === mode
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {mode === 'printed' ? '🖨 Printed Prescription' : '✍️ Handwritten Prescription'}
          </button>
        ))}
      </div>

      <div className={`grid gap-6 ${previewUrl ? 'lg:grid-cols-2' : 'grid-cols-1'}`}>
        {/* Upload card */}
        <Card>
          <CardHeader>
            <CardTitle>Upload Prescription</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg border-gray-300 bg-gray-50">
                <Upload className="h-10 w-10 text-gray-400 mb-3" />
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                {file && (
                  <p className="text-sm text-gray-600 mt-2">
                    <span className="font-medium">{file.name}</span>
                  </p>
                )}
              </div>
              <div className="text-xs text-gray-500 bg-yellow-50 border border-yellow-200 rounded p-3">
                <strong>Mode:</strong> {writingMode === 'handwritten' ? 'Handwritten — preserves thin strokes, no binarisation' : 'Printed — adaptive contrast & threshold for clear text'}
              </div>
              <Button type="submit" disabled={!file} isLoading={loading} className="w-full">
                Analyze {writingMode === 'handwritten' ? 'Handwritten' : 'Printed'} Prescription
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Document preview */}
        {previewUrl && (
          <Card>
            <CardHeader><CardTitle>Original Document</CardTitle></CardHeader>
            <CardContent>
              <img
                src={previewUrl}
                alt="Uploaded prescription"
                className="w-full max-h-80 object-contain rounded border"
              />
            </CardContent>
          </Card>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Review warning */}
          {reviewCount > 0 && (
            <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-md">
              <AlertTriangle className="h-5 w-5 mt-0.5 shrink-0" />
              <div>
                <strong>{reviewCount} medication{reviewCount > 1 ? 's' : ''} flagged for manual review</strong> — low OCR confidence.
                Verify these against the original prescription before use.
              </div>
            </div>
          )}

          {/* Medications table */}
          <Card>
            <CardHeader className="bg-green-50 border-b flex flex-row items-center justify-between">
              <CardTitle className="flex items-center text-green-800">
                <CheckCircle className="mr-2 h-5 w-5" />
                Extraction Complete — {medications.length} medication{medications.length !== 1 ? 's' : ''} found
              </CardTitle>
              {result.ocr_confidence > 0 && (
                <span className="text-sm text-gray-500">
                  OCR confidence: {(result.ocr_confidence * 100).toFixed(1)}%
                </span>
              )}
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Medication Name (as recognized)</TableHead>
                    <TableHead>Strength / Dose</TableHead>
                    <TableHead>Frequency</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Meal</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Review</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {medications.length > 0 ? (
                    medications.map((med: any, i: number) => (
                      <TableRow key={i} className={med.requires_review ? 'bg-amber-50' : ''}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <Pill className="h-4 w-4 text-blue-500 shrink-0" />
                            <span>{med.name_transcribed || med.normalized_name}</span>
                          </div>
                        </TableCell>
                        <TableCell>{med.strength || med.dosage || '—'}</TableCell>
                        <TableCell>{med.frequency || '—'}</TableCell>
                        <TableCell>{med.duration || '—'}</TableCell>
                        <TableCell>{med.meal_instructions || '—'}</TableCell>
                        <TableCell>{confidenceBadge(med.confidence || 0)}</TableCell>
                        <TableCell>
                          {med.requires_review ? (
                            <Badge variant="warning">Verify</Badge>
                          ) : (
                            <Badge variant="success">OK</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-6 text-gray-500">
                        No medications detected. Ensure the image is clear and the correct mode is selected.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* AI Explanation */}
          {result.llm_explanation && (
            <Card>
              <CardHeader><CardTitle>AI Pharmacist Explanation</CardTitle></CardHeader>
              <CardContent>
                <div className="p-4 bg-blue-50 rounded-lg text-sm text-blue-900 border border-blue-200 whitespace-pre-wrap">
                  {result.llm_explanation}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Raw OCR text */}
          {result.ocr_text && (
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><FileText className="h-4 w-4" /> Raw OCR Text</CardTitle></CardHeader>
              <CardContent>
                <div className="p-4 bg-gray-900 text-gray-200 rounded-lg text-xs font-mono max-h-48 overflow-y-auto whitespace-pre-wrap">
                  {result.ocr_text}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Disclaimer */}
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
            <strong>⚠ Medical Safety Notice:</strong> {result.disclaimer}
          </div>
        </div>
      )}
    </div>
  );
}
