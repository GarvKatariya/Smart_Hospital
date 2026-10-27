'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { adminAPI, departmentAPI, DepartmentInput } from '@/lib/api';

interface Department extends DepartmentInput { id: string; created_at: string }
interface Doctor {
  id: string;
  full_name: string;
  email: string;
  department_name: string;
  specialization: string | null;
  experience_years: number | null;
  is_available: boolean;
}
import { UserPlus, Users, Building, Stethoscope } from 'lucide-react';

export default function DoctorManagementPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    department_id: '',
    specialization: '',
    qualification: '',
    experience_years: '',
  });

  const fetchDoctors = async () => {
    try {
      const res = await adminAPI.listDoctors();
      setDoctors(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    let active = true;
    adminAPI.listDoctors().then(response => {
      if (active) setDoctors(response.data);
    }).catch(() => {
      if (active) setError('Could not load doctors. Confirm your administrator access.');
    });
    departmentAPI.list().then(response => {
      if (active) setDepartments(response.data);
    }).catch(() => {
      if (active) setError('Could not load departments.');
    });
    return () => { active = false; };
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        ...form,
        experience_years: form.experience_years ? parseInt(form.experience_years) : undefined,
      };
      const res = await adminAPI.createDoctor(payload);
      setSuccess(res.data.message || 'Doctor created successfully');
      setForm({ full_name: '', email: '', password: '', department_id: '', specialization: '', qualification: '', experience_years: '' });
      setShowForm(false);
      fetchDoctors();
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setError(typeof detail === 'string' ? detail : 'Failed to create doctor');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Doctor Management</h2>
          <p className="text-muted-foreground">Create and manage hospital doctors.</p>
        </div>
        <Button onClick={() => { setShowForm(!showForm); setError(''); setSuccess(''); }}>
          <UserPlus size={16} className="mr-2" />
          {showForm ? 'Cancel' : 'Add Doctor'}
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">{error}</div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">{success}</div>
      )}

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Doctor</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Full Name"
                  placeholder="Dr. John Smith"
                  value={form.full_name}
                  onChange={e => setForm({...form, full_name: e.target.value})}
                  required
                />
                <Input
                  label="Email"
                  type="email"
                  placeholder="doctor@hospital.com"
                  value={form.email}
                  onChange={e => setForm({...form, email: e.target.value})}
                  required
                />
                  <Input
                  label="Password"
                  type="password"
                  placeholder="At least 8 characters"
                  minLength={8}
                  value={form.password}
                  onChange={e => setForm({...form, password: e.target.value})}
                  required
                />
                <div className="space-y-1">
                  <label className="text-sm font-medium">Department</label>
                  <div className="relative">
                    <Building className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                    <select
                      className="w-full pl-10 pr-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                      value={form.department_id}
                      onChange={e => setForm({...form, department_id: e.target.value})}
                      required
                    >
                      <option value="">Select Department</option>
                      {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                  </div>
                </div>
                <Input
                  label="Specialization"
                  placeholder="e.g. Cardiologist"
                  value={form.specialization}
                  onChange={e => setForm({...form, specialization: e.target.value})}
                />
                <Input
                  label="Qualification"
                  placeholder="e.g. MD, MBBS"
                  value={form.qualification}
                  onChange={e => setForm({...form, qualification: e.target.value})}
                />
                <Input
                  label="Experience (years)"
                  type="number"
                  placeholder="e.g. 10"
                  value={form.experience_years}
                  onChange={e => setForm({...form, experience_years: e.target.value})}
                />
              </div>
              <Button type="submit" isLoading={loading} className="w-full md:w-auto">
                <Stethoscope size={16} className="mr-2" />
                Create Doctor
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Users size={20} className="mr-2" />
            All Doctors ({doctors.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Specialization</TableHead>
                <TableHead>Experience</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {doctors.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                    No doctors found. Click &quot;Add Doctor&quot; to create one.
                  </TableCell>
                </TableRow>
              ) : (
                doctors.map(doc => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">{doc.full_name}</TableCell>
                    <TableCell className="text-gray-500">{doc.email}</TableCell>
                    <TableCell>
                      <Badge variant="default">{doc.department_name}</Badge>
                    </TableCell>
                    <TableCell>{doc.specialization || '—'}</TableCell>
                    <TableCell>{doc.experience_years ? `${doc.experience_years} yrs` : '—'}</TableCell>
                    <TableCell>
                      <Badge variant={doc.is_available ? 'success' : 'danger'}>
                        {doc.is_available ? 'Available' : 'Unavailable'}
                      </Badge>
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
