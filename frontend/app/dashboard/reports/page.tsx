'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import api from '@/lib/api';
import {
  FileText, Upload, CheckCircle, AlertCircle, TrendingUp, TrendingDown,
  ChevronDown, ChevronRight, Pill, Stethoscope, FlaskConical, ImageIcon,
  AlertTriangle, ShieldAlert, Eye
} from 'lucide-react';

type WritingMode = 'printed' | 'handwritten';

// Category display config
const CATEGORY_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode; variant: 'info' | 'success' | 'warning' | 'danger' | 'default' }> = {
  laboratory_report: { label: 'Laboratory Report', color: 'blue', icon: <FlaskConical className="h-4 w-4" />, variant: 'info' },
  prescription: { label: 'Medical Prescription', color: 'green', icon: <Pill className="h-4 w-4" />, variant: 'success' },
  diagnostic_imaging: { label: 'Diagnostic Imaging', color: 'purple', icon: <ImageIcon className="h-4 w-4" />, variant: 'info' },
  discharge_summary: { label: 'Discharge Summary', color: 'orange', icon: <Stethoscope className="h-4 w-4" />, variant: 'warning' },
  other_medical_document: { label: 'Medical Document', color: 'gray', icon: <FileText className="h-4 w-4" />, variant: 'default' },
  unknown: { label: 'Unknown Document', color: 'gray', icon: <AlertTriangle className="h-4 w-4" />, variant: 'warning' },
};

export default function ReportsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [writingMode, setWritingMode] = useState<WritingMode>('printed');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [showRawText, setShowRawText] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    setResult(null);
    setError('');
    if (f && f.type.startsWith('image/')) {
      setPreviewUrl(URL.createObjectURL(f));
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
    setShowRawText(false);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('writing_mode', writingMode);
      const res = await api.post('/api/reports/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process report. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Extract response data
  const extractedText: string = result?.extracted_text ?? '';
  const summary: string = result?.summary ?? '';
  const keyFindings: string[] = result?.key_findings ?? [];
  const abnormalValues: Record<string, string> = result?.abnormal_values ?? {};
  const importantValues: Record<string, string> = result?.important_values ?? {};
  const documentCategory: string = result?.document_category ?? 'unknown';
  const patientInsight = result?.patient_insight;
  const classificationConfidence: number = result?.classification_confidence ?? 0;
  const lowConfidenceWarning: boolean = result?.low_confidence_warning ?? false;
  const prescriptionData = result?.prescription_data ?? null;
  const labValues: any[] = result?.lab_values ?? [];
  const confidenceBreakdown = result?.confidence_breakdown ?? null;
  const hasAbnormal = Object.keys(abnormalValues).length > 0;
  const categoryConfig = CATEGORY_CONFIG[documentCategory] || CATEGORY_CONFIG.unknown;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Medical Document Scanner</h2>
        <p className="text-muted-foreground">Upload lab reports, prescriptions, or clinical documents for AI-assisted analysis.</p>
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
            {mode === 'printed' ? '🖨 Printed Document' : '✍️ Handwritten Document'}
          </button>
        ))}
      </div>

      <div className={`grid gap-6 ${previewUrl ? 'lg:grid-cols-2' : 'grid-cols-1'}`}>
        <Card>
          <CardHeader><CardTitle>Upload Document</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg border-gray-300 bg-gray-50">
                <Upload className="h-10 w-10 text-gray-400 mb-3" />
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={handleFileChange}
                  className="text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                {file && <p className="text-sm text-gray-600 mt-2 font-medium">{file.name}</p>}
              </div>
              <div className="text-xs text-gray-500 bg-yellow-50 border border-yellow-200 rounded p-3">
                <strong>Mode:</strong> {writingMode === 'handwritten' ? 'Handwritten — gentle enhancement, preserves stroke continuity' : 'Printed — adaptive binarisation for clean text extraction'}
              </div>
              <Button type="submit" disabled={!file} isLoading={loading} className="w-full">
                Upload &amp; Analyze
              </Button>
            </form>
          </CardContent>
        </Card>

        {previewUrl && (
          <Card>
            <CardHeader><CardTitle>Original Document</CardTitle></CardHeader>
            <CardContent>
              <img src={previewUrl} alt="Report preview" className="w-full max-h-80 object-contain rounded border" />
            </CardContent>
          </Card>
        )}
      </div>

      {error && (
        <Alert variant="error" title="Processing Error">
          {error}
        </Alert>
      )}

      {result && (
        <div className="space-y-4">
          {/* Header card with classification info */}
          <Card>
            <CardHeader className="bg-green-50 border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center text-green-800">
                  <CheckCircle className="mr-2 h-5 w-5" /> Analysis Complete
                </CardTitle>
                <div className="flex items-center gap-3">
                  {/* Document category badge */}
                  <Badge variant={categoryConfig.variant}>
                    <span className="flex items-center gap-1.5">
                      {categoryConfig.icon}
                      {categoryConfig.label}
                    </span>
                  </Badge>
                  {result.report_type && result.report_type !== categoryConfig.label && (
                    <Badge variant="info">{result.report_type}</Badge>
                  )}
                  {result.ocr_confidence > 0 && (
                    <span className={`text-sm ${result.ocr_confidence < 0.6 ? 'text-amber-600 font-medium' : 'text-gray-500'}`}>
                      OCR: {(result.ocr_confidence * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6 space-y-6">

              {/* Low confidence warning */}
              {lowConfidenceWarning && (
                <Alert variant="warning" title="Low OCR Confidence">
                  The text extraction confidence is low. Some values may be incorrect.
                  Please review the extracted text carefully before relying on the results.
                </Alert>
              )}

              {result.ocr_engine === 'mock' && (
                <Alert variant="warning" title="Demo OCR is active">
                  This system returned placeholder text instead of reading your upload. Extracted values and the insight below are sample-only and may not describe this document.
                </Alert>
              )}

              {/* Classification confidence */}
              {classificationConfidence > 0 && classificationConfidence < 0.5 && (
                <Alert variant="warning" title="Low Classification Confidence">
                  The document type could not be determined with high confidence
                  ({(classificationConfidence * 100).toFixed(0)}%). Results may need manual verification.
                </Alert>
              )}

              {/* Confidence breakdown for prescriptions */}
              {confidenceBreakdown && documentCategory === 'prescription' && (
                <div className="text-xs text-gray-500 bg-gray-50 border rounded-lg p-3 space-y-1">
                  <p className="font-medium text-gray-700 mb-1">Confidence Breakdown</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    <ConfBadge label="Classification" val={confidenceBreakdown.document_classification} />
                    <ConfBadge label="Field Extraction" val={confidenceBreakdown.field_extraction} />
                    {confidenceBreakdown.medicine_name != null && (
                      <ConfBadge label="Medicine Names" val={confidenceBreakdown.medicine_name} />
                    )}
                    {confidenceBreakdown.dosage_duration != null && (
                      <ConfBadge label="Dosage / Duration" val={confidenceBreakdown.dosage_duration} />
                    )}
                  </div>
                  <p className="text-gray-400 mt-1">An overall OCR score does not imply every extracted field is correct.</p>
                </div>
              )}

              {/* Summary */}
              <div>
                <h3 className="text-base font-semibold mb-2">Summary</h3>
                <div className="p-4 bg-gray-50 rounded-lg border text-sm text-gray-800 whitespace-pre-wrap">
                  {summary || 'No summary available.'}
                </div>
              </div>

              <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <h3 className="text-base font-semibold text-blue-950">What this may mean</h3>
                  {patientInsight?.status === 'ai' && <Badge variant="info">AI explanation</Badge>}
                  {patientInsight?.status === 'basic' && <Badge variant="default">Basic explanation</Badge>}
                  {patientInsight?.status === 'sample_only' && <Badge variant="warning">Demo sample</Badge>}
                </div>
                <p className="text-sm text-blue-950 whitespace-pre-wrap">
                  {patientInsight?.text || 'There is not enough reliable extracted information to explain this document.'}
                </p>
                {patientInsight?.notice && (
                  <p className="mt-2 text-xs font-medium text-amber-800">{patientInsight.notice}</p>
                )}
                <p className="mt-3 text-xs text-gray-600">
                  This explanation is not a diagnosis. A clinician should interpret results in the context of your health and the original report.
                </p>
              </div>

              {/* --- PRESCRIPTION-SPECIFIC UI --- */}
              {documentCategory === 'prescription' && prescriptionData && (
                <PrescriptionDetails data={prescriptionData} />
              )}

              {/* --- LAB REPORT-SPECIFIC UI --- */}
              {(documentCategory === 'laboratory_report' || (documentCategory === 'other_medical_document' && Object.keys(importantValues).length > 0)) && (
                <>
                  {/* Abnormal values alert */}
                  {hasAbnormal && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-red-800 mb-2 flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" /> Abnormal Values
                      </h3>
                      <div className="grid gap-2">
                        {Object.entries(abnormalValues).map(([k, v]) => (
                          <div key={k} className="flex items-center justify-between text-sm">
                            <span className="font-medium text-red-700">{k}</span>
                            <span className="text-red-600">{v as string}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Extracted Lab Values table */}
                  {Object.keys(importantValues).length > 0 ? (
                    <div>
                      <h3 className="text-base font-semibold mb-2 flex items-center gap-2">
                        <FlaskConical className="h-4 w-4" /> Extracted Lab Values
                      </h3>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Test</TableHead>
                            <TableHead>Value</TableHead>
                            <TableHead>Reference Range</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Confidence</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {labValues.length > 0 ? (
                            labValues.map((item: any, idx: number) => {
                              const status = item.status || 'unknown';
                              return (
                                <TableRow key={idx} className={status === 'high' || status === 'low' ? 'bg-red-50' : ''}>
                                  <TableCell className="font-medium">{item.test_name}</TableCell>
                                  <TableCell>{item.value} {item.unit}</TableCell>
                                  <TableCell className="text-gray-500 text-xs">
                                    {item.reference_range || '—'}
                                  </TableCell>
                                  <TableCell>
                                    {status === 'high' ? (
                                      <Badge variant="danger">High</Badge>
                                    ) : status === 'low' ? (
                                      <Badge variant="danger">Low</Badge>
                                    ) : status === 'normal' ? (
                                      <Badge variant="success">Normal</Badge>
                                    ) : (
                                      <Badge variant="warning">Unknown</Badge>
                                    )}
                                  </TableCell>
                                  <TableCell>
                                    <span className={`text-xs ${(item.confidence || 0) < 0.7 ? 'text-amber-600' : 'text-gray-500'}`}>
                                      {((item.confidence || 0) * 100).toFixed(0)}%
                                    </span>
                                  </TableCell>
                                </TableRow>
                              );
                            })
                          ) : (
                            // Fallback to important_values if lab_values not available
                            Object.entries(importantValues).map(([test, val]) => {
                              const isAbnormal = test in abnormalValues;
                              return (
                                <TableRow key={test} className={isAbnormal ? 'bg-red-50' : ''}>
                                  <TableCell className="font-medium">{test}</TableCell>
                                  <TableCell>{val as string}</TableCell>
                                  <TableCell className="text-gray-500 text-xs">—</TableCell>
                                  <TableCell>
                                    {isAbnormal ? (
                                      <Badge variant="danger">Abnormal</Badge>
                                    ) : (
                                      <Badge variant="success">Normal</Badge>
                                    )}
                                  </TableCell>
                                  <TableCell>—</TableCell>
                                </TableRow>
                              );
                            })
                          )}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <Alert variant="info" title="No Laboratory Results">
                      No standard laboratory values were detected in this document.
                    </Alert>
                  )}
                </>
              )}

              {/* --- NO LAB RESULTS MESSAGE for non-lab documents --- */}
              {documentCategory !== 'laboratory_report' &&
               documentCategory !== 'prescription' &&
               documentCategory !== 'other_medical_document' &&
               Object.keys(importantValues).length === 0 && (
                <Alert variant="info" title="No Laboratory Results">
                  No laboratory results detected. This document was classified as: {categoryConfig.label}.
                </Alert>
              )}

              {/* Key findings */}
              {keyFindings.length > 0 && (
                <div>
                  <h3 className="text-base font-semibold mb-2">Key Findings</h3>
                  <ul className="space-y-1">
                    {keyFindings.map((f: string, i: number) => (
                      <li key={i} className={`text-sm flex items-start gap-2 ${
                        f.startsWith('⚠') ? 'text-amber-700 bg-amber-50 p-2 rounded' : 'text-gray-700'
                      }`}>
                        <span className="text-blue-500 mt-0.5 shrink-0">•</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Raw OCR — collapsible */}
              {extractedText && (
                <div>
                  <button
                    onClick={() => setShowRawText(!showRawText)}
                    className="flex items-center gap-2 text-base font-semibold mb-2 hover:text-blue-600 transition-colors"
                  >
                    {showRawText ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    <FileText className="h-4 w-4" />
                    Extracted Text (OCR)
                  </button>
                  {showRawText && (
                    <div className="p-4 bg-gray-900 text-gray-200 rounded-lg text-xs font-mono max-h-64 overflow-y-auto whitespace-pre-wrap">
                      {extractedText}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Prescription Details sub-component
// ---------------------------------------------------------------------------

function PrescriptionDetails({ data }: { data: any }) {
  const patientInfo = data?.patient_info || {};
  const medications: any[] = data?.medications || [];
  const clinicalInfo = data?.clinical_info || {};

  return (
    <div className="space-y-5">
      {/* Patient & Doctor info */}
      {Object.keys(patientInfo).length > 0 && (
        <div>
          <h3 className="text-base font-semibold mb-2 flex items-center gap-2">
            <Stethoscope className="h-4 w-4" /> Patient &amp; Doctor Information
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {patientInfo.patient_name && (
              <InfoField label="Patient" value={patientInfo.patient_name} />
            )}
            {patientInfo.patient_age && (
              <InfoField label="Age" value={String(patientInfo.patient_age)} />
            )}
            {patientInfo.patient_sex && (
              <InfoField label="Sex" value={patientInfo.patient_sex} />
            )}
            {patientInfo.doctor && (
              <InfoField label="Doctor" value={patientInfo.doctor} />
            )}
            {patientInfo.date && (
              <InfoField label="Date" value={patientInfo.date} />
            )}
          </div>
        </div>
      )}

      {/* Clinical info */}
      {(clinicalInfo.chief_complaints || clinicalInfo.diagnosis || clinicalInfo.clinical_findings) && (
        <div>
          <h3 className="text-base font-semibold mb-2">Clinical Information</h3>
          <div className="space-y-2">
            {clinicalInfo.chief_complaints && (
              <InfoField label="Chief Complaints" value={clinicalInfo.chief_complaints} block />
            )}
            {clinicalInfo.clinical_findings && (
              <InfoField label="Clinical Findings" value={clinicalInfo.clinical_findings} block />
            )}
            {clinicalInfo.diagnosis && (
              <InfoField label="Diagnosis" value={clinicalInfo.diagnosis} block />
            )}
          </div>
        </div>
      )}

      {/* Medications table */}
      <div>
        <h3 className="text-base font-semibold mb-2 flex items-center gap-2">
          <Pill className="h-4 w-4" /> Medications
          {medications.length > 0 && (
            <span className="text-sm font-normal text-gray-500">
              ({medications.length} found)
            </span>
          )}
        </h3>
        {medications.length > 0 ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Medicine</TableHead>
                  <TableHead>Strength / Dose</TableHead>
                  <TableHead>Schedule</TableHead>
                  <TableHead>Frequency</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Instructions</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {medications.map((med: any, idx: number) => {
                  const needsReview = med.requires_review;
                  const confidence = med.confidence || 0;
                  const strengthDisplay = med.strength || med.dosage || '—';
                  const scheduleDisplay = med.dose_schedule || '—';
                  return (
                    <TableRow key={idx} className={needsReview ? 'bg-amber-50' : ''}>
                      <TableCell className="text-gray-400 text-xs">
                        {med.entry_number ?? idx + 1}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-start gap-2">
                          <div>
                            <span className="font-medium">{med.name_transcribed || med.name_raw || '—'}</span>
                            {med.ingredient_notes && (
                              <p className="text-xs text-gray-500 mt-0.5">{med.ingredient_notes}</p>
                            )}
                          </div>
                          {needsReview && (
                            <span title={`OCR confidence: ${(confidence * 100).toFixed(0)}% — needs verification`}>
                              <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0 mt-0.5" />
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-gray-600">{strengthDisplay}</TableCell>
                      <TableCell className="text-gray-600 font-mono text-xs">{scheduleDisplay}</TableCell>
                      <TableCell className="text-gray-600 text-xs">{med.frequency || '—'}</TableCell>
                      <TableCell className="text-gray-600 text-xs">{med.duration || '—'}</TableCell>
                      <TableCell className="text-gray-600 text-xs">
                        {[med.meal_instructions, med.route].filter(Boolean).join(', ') || '—'}
                      </TableCell>
                      <TableCell>
                        {needsReview ? (
                          <Badge variant="warning">
                            <span className="flex items-center gap-1">
                              <Eye className="h-3 w-3" /> Review
                            </span>
                          </Badge>
                        ) : (
                          <Badge variant="success">OK</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        ) : (
          <Alert variant="warning" title="No Medications Extracted">
            No medications could be automatically extracted from this document. Please review the original document manually.
          </Alert>
        )}
      </div>

      {/* Advice & follow-up */}
      {(clinicalInfo.advice || clinicalInfo.follow_up) && (
        <div>
          <h3 className="text-base font-semibold mb-2">Advice &amp; Follow-up</h3>
          <div className="space-y-2">
            {clinicalInfo.advice && (
              <InfoField label="Advice" value={clinicalInfo.advice} block />
            )}
            {clinicalInfo.follow_up && (
              <InfoField label="Follow-up" value={clinicalInfo.follow_up} block />
            )}
          </div>
        </div>
      )}

      {/* Review warning */}
      {medications.some((m: any) => m.requires_review) && (
        <Alert variant="warning" title="Manual Review Required">
          Some medications are flagged for review due to low OCR confidence or ambiguous names.
          Items marked with ⚠ should be verified against the original document before use.
        </Alert>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Confidence breakdown badge
// ---------------------------------------------------------------------------

function ConfBadge({ label, val }: { label: string; val: number | null }) {
  if (val == null) return null;
  const pct = Math.round(val * 100);
  const color = pct >= 80 ? 'text-green-700' : pct >= 55 ? 'text-amber-600' : 'text-red-600';
  return (
    <div className="flex flex-col">
      <span className="text-gray-500">{label}</span>
      <span className={`font-medium ${color}`}>{pct}%</span>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Shared helper component
// ---------------------------------------------------------------------------

function InfoField({ label, value, block }: { label: string; value: string; block?: boolean }) {
  if (block) {
    return (
      <div className="bg-gray-50 border rounded-lg p-3">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
        <p className="text-sm text-gray-800 mt-1">{value}</p>
      </div>
    );
  }
  return (
    <div className="bg-gray-50 border rounded-lg p-3">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
      <p className="text-sm text-gray-800 mt-1 font-medium">{value}</p>
    </div>
  );
}
