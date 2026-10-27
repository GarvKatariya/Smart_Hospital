'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { triageAPI } from '@/lib/api';
import { Clock, Users } from 'lucide-react';
import { Alert } from '@/components/ui/Alert';

interface QueueItem {
  id: string;
  patient_name: string;
  queue_number: number;
  priority: string;
  status: 'waiting' | 'in_progress';
  estimated_wait: number | null;
  check_in_time: string | null;
  is_demo?: boolean;
  notes?: string | null;
}

function getPriorityColor(priority: string): 'danger' | 'warning' | 'info' | 'success' | 'default' {
  switch ((priority || '').toLowerCase()) {
    case 'emergency': return 'danger';
    case 'high': case 'urgent': return 'warning';
    case 'medium': case 'standard': return 'info';
    case 'low': case 'non-urgent': return 'success';
    default: return 'default';
  }
}

export default function QueuePage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  useEffect(() => {
    triageAPI.getQueue()
      .then(res => {
        const data = Array.isArray(res.data) ? res.data : [];
        setQueue(data);
      })
      .catch(() => setError('Could not load the patient queue. Staff access is required.'))
      .finally(() => setLoading(false));
  }, []);

  const updateStatus = async (entry: QueueItem, status: 'in_progress' | 'completed' | 'cancelled') => {
    setUpdatingId(entry.id);
    setError('');
    try {
      await triageAPI.updateQueueStatus(entry.id, status);
      const response = await triageAPI.getQueue();
      setQueue(Array.isArray(response.data) ? response.data : []);
    } catch {
      setError('Could not update this queue entry. Refresh and try again.');
    } finally {
      setUpdatingId(null);
    }
  };

  const avgWait = queue.length > 0
    ? Math.floor(queue.reduce((a, b) => a + (b.estimated_wait || 0), 0) / queue.length)
    : 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Triage Queue Status</h2>
        <p className="text-muted-foreground">Live tracking of patient wait times and urgency prioritization.</p>
      </div>

      {queue.some(item => item.is_demo) && (
        <Alert variant="info">This queue includes synthetic demo records loaded from <code>data/demo_queue.json</code>. They are for demonstration only and do not represent real patients.</Alert>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-800">Patients in Queue</p>
              <h3 className="text-3xl font-bold text-blue-900">{queue.length}</h3>
            </div>
            <Users className="h-10 w-10 text-blue-300" />
          </CardContent>
        </Card>
        <Card className="bg-orange-50 border-orange-200">
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-800">Avg Wait Time</p>
              <h3 className="text-3xl font-bold text-orange-900">{avgWait} min</h3>
            </div>
            <Clock className="h-10 w-10 text-orange-300" />
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200">
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-800">Emergency Cases</p>
              <h3 className="text-3xl font-bold text-red-900">
                {queue.filter(q => (q.priority || '').toLowerCase() === 'emergency').length}
              </h3>
            </div>
            <Users className="h-10 w-10 text-red-300" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Queue #</TableHead>
                <TableHead>Patient</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Check-in Time</TableHead>
                <TableHead>Est. Wait</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {error ? (
                <TableRow><TableCell colSpan={7}><Alert variant="error">{error}</Alert></TableCell></TableRow>
              ) : loading ? (
                <TableRow><TableCell colSpan={7} className="py-8 text-center">Loading queue…</TableCell></TableRow>
              ) : queue.length === 0 ? (
                <TableRow><TableCell colSpan={7} className="text-center py-8 text-gray-500">No patients currently in queue.</TableCell></TableRow>
              ) : (
                queue.map((q, i) => (
                  <TableRow key={q.id}>
                    <TableCell className="font-bold">Q-{String(q.queue_number || i + 1).padStart(3, '0')}</TableCell>
                    <TableCell>{q.patient_name || 'Patient'}</TableCell>
                    <TableCell>
                      <Badge variant={getPriorityColor(q.priority)}>
                        {(q.priority || 'unknown').toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell><Badge variant={q.status === 'in_progress' ? 'info' : 'default'}>{q.status.replace('_', ' ')}</Badge></TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {q.check_in_time ? new Date(q.check_in_time).toLocaleString() : '—'}
                    </TableCell>
                    <TableCell>
                      <span className="flex items-center text-sm font-medium">
                        <Clock size={14} className="mr-1 text-gray-400"/>
                        {q.estimated_wait != null ? `${q.estimated_wait} min` : 'Immediate'}
                      </span>
                    </TableCell>
                    <TableCell>
                      {q.status === 'waiting' ? (
                        <Button size="sm" onClick={() => void updateStatus(q, 'in_progress')} isLoading={updatingId === q.id}>Call</Button>
                      ) : (
                        <div className="flex gap-2">
                          <Button size="sm" onClick={() => void updateStatus(q, 'completed')} isLoading={updatingId === q.id}>Complete</Button>
                          <Button size="sm" variant="danger" onClick={() => void updateStatus(q, 'cancelled')} disabled={updatingId === q.id}>Cancel</Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
