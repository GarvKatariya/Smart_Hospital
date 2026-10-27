'use client';

import { useCallback, useEffect, useState } from 'react';
import { Activity, CheckCircle2, RefreshCw, XCircle } from 'lucide-react';
import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import { adminAPI } from '@/lib/api';

interface ModelStatus {
  name: string;
  display_name: string;
  version: string | null;
  is_active: boolean;
  artifact_present: boolean;
  training_date: string | null;
  metrics: Record<string, number> | null;
}

export default function ModelsPage() {
  const [models, setModels] = useState<ModelStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadModels = useCallback(async () => {
    try {
      const response = await adminAPI.getModelStatus();
      setModels(response.data?.models ?? []);
      setError('');
    } catch {
      setError('Could not load model status. Confirm that you are signed in as an administrator.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    adminAPI.getModelStatus()
      .then(response => {
        if (active) setModels(response.data?.models ?? []);
      })
      .catch(() => {
        if (active) setError('Could not load model status. Confirm that you are signed in as an administrator.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">AI Model Status</h2>
          <p className="text-muted-foreground">Artifact availability and registered model versions.</p>
          <p className="mt-1 text-xs text-muted-foreground">“Missing” means the expected model artifact is not present. Prescription extraction is rules-based in this project; it is shown separately from trained neural models.</p>
        </div>
        <Button variant="outline" onClick={() => void loadModels()} disabled={loading}>
          <RefreshCw size={16} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />Refresh
        </Button>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Activity size={18} />Registered Models</CardTitle></CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Model</TableHead><TableHead>Version</TableHead><TableHead>Artifact</TableHead><TableHead>Active</TableHead><TableHead>Training date</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={5} className="py-8 text-center">Loading model status…</TableCell></TableRow>
              ) : models.length === 0 ? (
                <TableRow><TableCell colSpan={5} className="py-8 text-center text-gray-500">No model status records were returned.</TableCell></TableRow>
              ) : models.map(model => (
                <TableRow key={model.name}>
                  <TableCell className="font-medium">{model.display_name}</TableCell>
                  <TableCell>{model.version ?? 'Not registered'}</TableCell>
                  <TableCell>
                    <Badge variant={model.artifact_present ? 'success' : 'warning'}>
                      {model.artifact_present ? 'Available' : 'Missing'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-2">
                      {model.is_active ? <CheckCircle2 size={16} className="text-green-600" /> : <XCircle size={16} className="text-gray-400" />}
                      {model.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </TableCell>
                  <TableCell>{model.training_date ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
