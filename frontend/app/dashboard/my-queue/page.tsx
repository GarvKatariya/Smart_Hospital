'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { RefreshCw, Stethoscope, Users } from 'lucide-react';
import { triageAPI } from '@/lib/api';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

interface PatientQueueEntry {
  id: string;
  queue_number: number;
  priority: string;
  status: 'waiting' | 'in_progress';
  estimated_wait: number | null;
  patients_ahead: number;
  department_name: string;
  check_in_time: string | null;
}

export default function MyQueuePage() {
  const [entries, setEntries] = useState<PatientQueueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await triageAPI.getMyQueue();
      setEntries(Array.isArray(response.data) ? response.data : []);
    } catch {
      setError('Could not load your queue status. Please refresh and try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Triage Queue</h1>
          <p className="mt-1 text-sm text-gray-600">Track the status and estimated wait for your own active triage entries.</p>
        </div>
        <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Refresh
        </Button>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {loading ? (
        <Card><CardContent className="py-10 text-center text-sm text-gray-500">Loading your queue…</CardContent></Card>
      ) : entries.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <Users className="h-10 w-10 text-gray-400" />
            <div>
              <h2 className="font-semibold">You have no active queue entry</h2>
              <p className="mt-1 text-sm text-gray-500">Complete an AI triage assessment to join the care queue.</p>
            </div>
            <Link href="/dashboard/triage" className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
              <Stethoscope className="mr-2 h-4 w-4" />Start AI triage
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {entries.map(entry => (
            <Card key={entry.id}>
              <CardHeader className="flex flex-row items-center justify-between gap-3 border-b bg-blue-50">
                <CardTitle className="text-blue-950">Queue Q-{String(entry.queue_number).padStart(3, '0')}</CardTitle>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${entry.status === 'in_progress' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-900'}`}>
                  {entry.status.replace('_', ' ')}
                </span>
              </CardHeader>
              <CardContent className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
                <div><p className="text-xs text-gray-500">Department</p><p className="font-medium">{entry.department_name}</p></div>
                <div><p className="text-xs text-gray-500">Priority</p><p className="font-medium capitalize">{entry.priority}</p></div>
                <div><p className="text-xs text-gray-500">People ahead</p><p className="font-medium">{entry.patients_ahead}</p></div>
                <div><p className="text-xs text-gray-500">Estimated wait</p><p className="font-medium">{entry.status === 'in_progress' ? 'You are being seen' : `${entry.estimated_wait ?? '—'} min`}</p></div>
              </CardContent>
            </Card>
          ))}
          <p className="text-xs text-gray-500">Queue order and wait estimates can change as staff update patient status. For an emergency, contact local emergency services; do not wait for this page.</p>
        </div>
      )}
    </div>
  );
}
