'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { AlertTriangle, CheckCircle2, ClipboardPlus, HeartPulse } from 'lucide-react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { TriageInput, triageAPI } from '@/lib/api';

type TriageResult = {
  urgency: string;
  confidence: number;
  queue_number: number;
  estimated_wait: number;
  override_applied: boolean;
  disclaimer: string;
};

const redFlagOptions = [
  'chest pain',
  'shortness of breath',
  'severe bleeding',
  'loss of consciousness',
];

export default function TriagePage() {
  const [symptoms, setSymptoms] = useState('');
  const [severity, setSeverity] = useState(3);
  const [duration, setDuration] = useState('2 days');
  const [age, setAge] = useState('30');
  const [consciousness, setConsciousness] = useState('alert');
  const [vitals, setVitals] = useState<Record<string, string>>({});
  const [redFlags, setRedFlags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<TriageResult | null>(null);

  const toggleFlag = (flag: string) => setRedFlags(current =>
    current.includes(flag) ? current.filter(item => item !== flag) : [...current, flag]
  );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    const payload: TriageInput = {
      symptoms: symptoms.trim(),
      severity,
      duration: duration.trim(),
      age: Number(age),
      vital_signs: Object.fromEntries(
        Object.entries(vitals).filter(([, value]) => value !== '').map(([key, value]) => [key, Number(value)])
      ),
      consciousness_level: consciousness,
      red_flag_symptoms: redFlags,
    };
    try {
      const response = await triageAPI.predict(payload);
      setResult(response.data);
    } catch (cause: unknown) {
      const detail = axios.isAxiosError<{ detail?: unknown }>(cause) ? cause.response?.data?.detail : undefined;
      setError(typeof detail === 'string' ? detail : 'Triage could not be completed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const urgencyStyle = result?.urgency.toLowerCase() === 'emergency'
    ? 'border-red-300 bg-red-50 text-red-900'
    : result?.urgency.toLowerCase() === 'high'
      ? 'border-orange-300 bg-orange-50 text-orange-900'
      : 'border-blue-200 bg-blue-50 text-blue-900';

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI Triage</h1>
        <p className="mt-1 text-sm text-gray-600">Share your symptoms to receive an estimated urgency and join the care queue.</p>
      </div>

      <div role="note" className="flex gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <p><strong>For emergencies:</strong> If you may be in immediate danger, have severe chest pain, trouble breathing, heavy bleeding, or are losing consciousness, contact local emergency services or go to the nearest emergency department now. Do not wait for this tool.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><ClipboardPlus className="h-5 w-5 text-blue-600" /> Symptom assessment</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-5">
            <div>
              <label htmlFor="triage-symptoms" className="mb-1 block text-sm font-medium">What symptoms are you experiencing?</label>
              <textarea id="triage-symptoms" required minLength={3} maxLength={2000} value={symptoms} onChange={event => setSymptoms(event.target.value)} className="min-h-24 w-full rounded-md border border-gray-300 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Describe what you are feeling" />
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="triage-age" className="mb-1 block text-sm font-medium">Age</label>
                <input id="triage-age" required type="number" min="0" max="120" value={age} onChange={event => setAge(event.target.value)} className="h-10 w-full rounded-md border border-gray-300 px-3" />
              </div>
              <div>
                <label htmlFor="triage-severity" className="mb-1 block text-sm font-medium">Severity (1–10)</label>
                <input id="triage-severity" type="number" min="1" max="10" value={severity} onChange={event => setSeverity(Number(event.target.value))} className="h-10 w-full rounded-md border border-gray-300 px-3" />
              </div>
              <div>
                <label htmlFor="triage-duration" className="mb-1 block text-sm font-medium">How long?</label>
                <input id="triage-duration" required value={duration} onChange={event => setDuration(event.target.value)} className="h-10 w-full rounded-md border border-gray-300 px-3" placeholder="e.g. 2 hours" />
              </div>
            </div>

            <fieldset>
              <legend className="mb-2 text-sm font-medium">Are any of these happening now?</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {redFlagOptions.map(flag => (
                  <label key={flag} className="flex items-center gap-2 rounded-md border border-gray-200 p-3 text-sm">
                    <input type="checkbox" checked={redFlags.includes(flag)} onChange={() => toggleFlag(flag)} className="h-4 w-4 accent-red-600" />
                    {flag[0].toUpperCase() + flag.slice(1)}
                  </label>
                ))}
              </div>
            </fieldset>

            <div>
              <label htmlFor="triage-consciousness" className="mb-1 block text-sm font-medium">Consciousness level</label>
              <select id="triage-consciousness" value={consciousness} onChange={event => setConsciousness(event.target.value)} className="h-10 w-full rounded-md border border-gray-300 bg-white px-3">
                <option value="alert">Alert and responding normally</option>
                <option value="confused">Confused</option>
                <option value="pain">Responds only to pain</option>
                <option value="unresponsive">Unresponsive</option>
              </select>
            </div>

            <details className="rounded-md border border-gray-200 p-3">
              <summary className="cursor-pointer text-sm font-medium">Optional vital signs</summary>
              <p className="my-2 text-xs text-gray-500">Enter only measurements you have. Do not delay urgent care to collect them.</p>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  ['heart_rate', 'Heart rate', '30', '250'],
                  ['blood_pressure_systolic', 'Systolic BP', '40', '300'],
                  ['blood_pressure_diastolic', 'Diastolic BP', '20', '200'],
                  ['temperature', 'Temperature (°C)', '25', '45'],
                  ['respiratory_rate', 'Breaths/min', '1', '80'],
                  ['oxygen_saturation', 'Oxygen (%)', '50', '100'],
                ].map(([key, label, min, max]) => (
                  <label key={key} className="text-sm text-gray-700">{label}
                    <input type="number" min={min} max={max} step="any" value={vitals[key] || ''} onChange={event => setVitals(current => ({ ...current, [key]: event.target.value }))} className="mt-1 h-9 w-full rounded-md border border-gray-300 px-2" />
                  </label>
                ))}
              </div>
            </details>

            {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            <Button type="submit" isLoading={loading} disabled={!symptoms.trim() || !age || !duration.trim()} className="w-full sm:w-auto">
              <HeartPulse className="mr-2 h-4 w-4" /> Get triage assessment
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card className={`border ${urgencyStyle}`} aria-live="polite">
          <CardContent className="p-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0" />
              <div className="w-full">
                <h2 className="text-lg font-semibold">Assessment: {result.urgency}</h2>
                <p className="mt-1 text-sm">Estimated wait: {result.estimated_wait} minutes · Queue number: {result.queue_number}</p>
                <p className="mt-1 text-sm">Model confidence: {Math.round(result.confidence * 100)}%</p>
                {result.override_applied && <p className="mt-3 font-medium">A safety rule raised this result to Emergency. Seek immediate in-person care.</p>}
                <Link href="/dashboard/my-queue" className="mt-3 inline-flex items-center font-medium underline">Track my queue</Link>
                <p className="mt-3 text-xs">{result.disclaimer} This result is saved to the hospital triage queue for staff review.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
