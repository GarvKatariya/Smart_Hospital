'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table';
import axios from 'axios';
import { departmentAPI, DepartmentInput } from '@/lib/api';

interface Department extends DepartmentInput {
  id: string;
  created_at: string;
}

const emptyForm: DepartmentInput = {
  name: '',
  description: '',
  floor: '',
  phone: '',
  is_active: true,
};

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [form, setForm] = useState<DepartmentInput>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadDepartments = useCallback(async () => {
    try {
      const response = await departmentAPI.listAll();
      setDepartments(response.data);
      setError('');
    } catch {
      setError('Could not load departments. Check your admin access and try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    departmentAPI.listAll()
      .then(response => {
        if (active) setDepartments(response.data);
      })
      .catch(() => {
        if (active) setError('Could not load departments. Check your admin access and try again.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      if (editingId) {
        await departmentAPI.update(editingId, form);
        setSuccess('Department updated.');
      } else {
        await departmentAPI.create(form);
        setSuccess('Department created.');
      }
      resetForm();
      await loadDepartments();
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setError(typeof detail === 'string' ? detail : 'Could not save the department.');
    } finally {
      setSaving(false);
    }
  };

  const editDepartment = (department: Department) => {
    setForm({
      name: department.name,
      description: department.description ?? '',
      floor: department.floor ?? '',
      phone: department.phone ?? '',
      is_active: department.is_active,
    });
    setEditingId(department.id);
    setError('');
    setSuccess('');
  };

  const toggleActive = async (department: Department) => {
    setError('');
    setSuccess('');
    try {
      await departmentAPI.update(department.id, { ...department, is_active: !department.is_active });
      setSuccess(`${department.name} ${department.is_active ? 'archived' : 'restored'}.`);
      await loadDepartments();
    } catch {
      setError('Could not change department status.');
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Department Management</h2>
        <p className="text-muted-foreground">Create, update, and archive hospital departments.</p>
      </div>

      {error && <Alert variant="error">{error}</Alert>}
      {success && <Alert variant="success">{success}</Alert>}

      <Card>
        <CardHeader><CardTitle>{editingId ? 'Edit Department' : 'Add Department'}</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Input label="Department name" value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} required />
              <Input label="Phone" value={form.phone} onChange={event => setForm({ ...form, phone: event.target.value })} />
              <Input label="Floor or location" value={form.floor} onChange={event => setForm({ ...form, floor: event.target.value })} />
              <Input label="Description" value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} />
            </div>
            <div className="flex gap-2">
              <Button type="submit" isLoading={saving}>{editingId ? 'Save Department' : 'Create Department'}</Button>
              {editingId && <Button type="button" variant="outline" onClick={resetForm}>Cancel</Button>}
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Departments ({departments.length})</CardTitle></CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader><TableRow>
              <TableHead>Name</TableHead><TableHead>Location</TableHead><TableHead>Phone</TableHead><TableHead>Status</TableHead><TableHead>Actions</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={5} className="py-8 text-center">Loading departments…</TableCell></TableRow>
              ) : departments.length === 0 ? (
                <TableRow><TableCell colSpan={5} className="py-8 text-center text-gray-500">No departments have been created.</TableCell></TableRow>
              ) : departments.map(department => (
                <TableRow key={department.id}>
                  <TableCell className="font-medium">{department.name}</TableCell>
                  <TableCell>{department.floor || '—'}</TableCell>
                  <TableCell>{department.phone || '—'}</TableCell>
                  <TableCell><Badge variant={department.is_active ? 'success' : 'default'}>{department.is_active ? 'Active' : 'Archived'}</Badge></TableCell>
                  <TableCell><div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => editDepartment(department)}>Edit</Button>
                    <Button size="sm" variant="outline" onClick={() => void toggleActive(department)}>{department.is_active ? 'Archive' : 'Restore'}</Button>
                  </div></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
