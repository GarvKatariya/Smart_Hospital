'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { adminAPI, type AdminPatient } from '@/lib/api';

export default function AdminPatientsPage() {
  const [patients, setPatients] = useState<AdminPatient[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async (offset = skip) => {
    setLoading(true); setError('');
    try { const response = await adminAPI.getPatients(offset); setPatients(response.data.patients); setTotal(response.data.total); setSkip(offset); }
    catch (cause: unknown) { setError(axios.isAxiosError(cause) ? cause.response?.data?.detail || 'Could not load the patient directory.' : 'Could not load the patient directory.'); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    let active = true;
    adminAPI.getPatients(0).then(response => {
      if (!active) return;
      setPatients(response.data.patients); setTotal(response.data.total); setSkip(0);
    }).catch((cause: unknown) => {
      if (active) setError(axios.isAxiosError(cause) ? cause.response?.data?.detail || 'Could not load the patient directory.' : 'Could not load the patient directory.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  return <div className="space-y-6 max-w-6xl mx-auto">
    <div><h1 className="text-2xl font-bold">Patient Directory</h1><p className="text-muted-foreground">Registered patient accounts and contact details.</p></div>
    <Card><CardHeader className="flex-row items-center justify-between"><CardTitle>{total} patients</CardTitle><Button variant="outline" onClick={() => void load()}>Refresh</Button></CardHeader><CardContent>
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      <Table><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Email</TableHead><TableHead>Phone</TableHead><TableHead>Status</TableHead><TableHead>Registered</TableHead></TableRow></TableHeader><TableBody>
        {loading ? <TableRow><TableCell colSpan={5} className="text-center">Loading patients…</TableCell></TableRow> : patients.length === 0 ? <TableRow><TableCell colSpan={5} className="text-center">No patients found.</TableCell></TableRow> : patients.map(patient => <TableRow key={patient.id}><TableCell>{patient.full_name}</TableCell><TableCell>{patient.email}</TableCell><TableCell>{patient.phone || '—'}</TableCell><TableCell>{patient.is_active ? 'Active' : 'Inactive'}</TableCell><TableCell>{patient.created_at ? new Date(patient.created_at).toLocaleDateString() : '—'}</TableCell></TableRow>)}
      </TableBody></Table>
      <div className="flex justify-end gap-2 mt-4"><Button variant="outline" disabled={loading || skip === 0} onClick={() => void load(Math.max(0, skip - 50))}>Previous</Button><Button variant="outline" disabled={loading || skip + patients.length >= total} onClick={() => void load(skip + 50)}>Next</Button></div>
    </CardContent></Card>
  </div>;
}
