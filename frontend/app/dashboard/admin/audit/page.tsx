'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { adminAPI, type AuditLogEntry } from '@/lib/api';

export default function AdminAuditPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true); setError('');
    try { const response = await adminAPI.getAuditLogs(); setLogs(response.data.logs); setTotal(response.data.total); }
    catch (cause: unknown) { setError(axios.isAxiosError(cause) ? cause.response?.data?.detail || 'Could not load audit history.' : 'Could not load audit history.'); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    let active = true;
    adminAPI.getAuditLogs().then(response => {
      if (!active) return;
      setLogs(response.data.logs); setTotal(response.data.total);
    }).catch((cause: unknown) => {
      if (active) setError(axios.isAxiosError(cause) ? cause.response?.data?.detail || 'Could not load audit history.' : 'Could not load audit history.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  return <div className="space-y-6 max-w-6xl mx-auto">
    <div><h1 className="text-2xl font-bold">Audit History</h1><p className="text-muted-foreground">Recent recorded changes and administrative activity.</p></div>
    <Card><CardHeader className="flex-row items-center justify-between"><CardTitle>{total} recorded events</CardTitle><Button variant="outline" onClick={() => void load()}>Refresh</Button></CardHeader><CardContent>
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      <p className="mb-4 text-sm text-muted-foreground">This is an accountability log of actions recorded by the application. Queue events show when a staff member called, completed, or cancelled a triage entry.</p>
      <Table><TableHeader><TableRow><TableHead>Time</TableHead><TableHead>Actor</TableHead><TableHead>Action</TableHead><TableHead>Resource</TableHead><TableHead>Details</TableHead></TableRow></TableHeader><TableBody>
        {loading ? <TableRow><TableCell colSpan={5} className="text-center">Loading audit history…</TableCell></TableRow> : logs.length === 0 ? <TableRow><TableCell colSpan={5} className="text-center">No audit events have been recorded.</TableCell></TableRow> : logs.map(log => <TableRow key={log.id}><TableCell>{log.created_at ? new Date(log.created_at).toLocaleString() : '—'}</TableCell><TableCell>{log.actor_name || 'System'}</TableCell><TableCell>{log.action.replaceAll('.', ' ').replaceAll('_', ' ')}</TableCell><TableCell>{log.resource_type.replaceAll('_', ' ')}{log.resource_id ? ` · ${log.resource_id.slice(0, 8)}` : ''}</TableCell><TableCell className="max-w-xs truncate">{log.details ? Object.entries(log.details).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${String(value)}`).join(' · ') : '—'}</TableCell></TableRow>)}
      </TableBody></Table>
    </CardContent></Card>
  </div>;
}
