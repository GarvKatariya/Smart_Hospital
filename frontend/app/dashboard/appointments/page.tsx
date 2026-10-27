'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { appointmentAPI, departmentAPI, doctorAPI, AppointmentRecommendationInput } from '@/lib/api';
import { formatDate, formatTime, getStatusColor } from '@/lib/utils';
import { Calendar, Clock, User, Building, Sparkles, AlertCircle } from 'lucide-react';
import { useAuth } from '@/lib/auth';

interface Department { id: string; name: string }
interface Doctor { id: string; full_name: string; is_available: boolean }
interface Appointment {
  id: string;
  appointment_date: string;
  appointment_time: string;
  status: string;
  reason: string;
  doctor?: { full_name: string };
  department?: { name: string };
}
interface RecommendedSlot {
  doctor_id: string;
  doctor_name: string;
  department_id: string;
  department_name: string;
  date: string;
  time: string;
  specialization?: string;
}

export default function AppointmentsPage() {
  const { user } = useAuth();
  const isPatient = user?.role?.toLowerCase() === 'patient';
  const [activeTab, setActiveTab] = useState<'my' | 'book' | 'ai'>('my');
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(false);
  const [appointmentsLoading, setAppointmentsLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ department_id: '', doctor_id: '', date: '', time: '', reason: '' });

  // AI recommendation state
  const [aiDeptId, setAiDeptId] = useState('');
  const [aiUrgency, setAiUrgency] = useState<AppointmentRecommendationInput['urgency']>('low');
  const [aiSlots, setAiSlots] = useState<RecommendedSlot[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [bookingSlot, setBookingSlot] = useState<string | null>(null);
  const [bookingSuccess, setBookingSuccess] = useState('');

  useEffect(() => {
    let active = true;
    appointmentAPI.list().then(response => {
      if (active) {
        setAppointments(response.data);
        setError('');
      }
    }).catch(() => {
      if (active) setError('Could not load appointments. Please refresh and try again.');
    }).finally(() => {
      if (active) setAppointmentsLoading(false);
    });
    departmentAPI.list().then(response => {
      if (active) setDepartments(response.data);
    }).catch(() => {
      if (active) setError('Could not load departments.');
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!form.department_id) return;
    let active = true;
    doctorAPI.list(form.department_id).then(response => {
      if (active) setDoctors(response.data.filter((doctor: Doctor) => doctor.is_available));
    }).catch(() => {
      if (active) setError('Could not load doctors for this department.');
    });
    return () => { active = false; };
  }, [form.department_id]);

  const fetchAppointments = async () => {
    setAppointmentsLoading(true);
    try {
      const res = await appointmentAPI.list();
      setAppointments(res.data);
      setError('');
    } catch {
      setError('Could not refresh appointments.');
    } finally {
      setAppointmentsLoading(false);
    }
  };

  const handleBook = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await appointmentAPI.create(form);
      setForm({ department_id: '', doctor_id: '', date: '', time: '', reason: '' });
      setActiveTab('my');
      fetchAppointments();
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setError(typeof detail === 'string' ? detail : 'Failed to book appointment.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await appointmentAPI.cancel(id);
      fetchAppointments();
    } catch {
      setError('Could not cancel this appointment.');
    }
  };

  const handleGetRecommendations = async () => {
    if (!aiDeptId) {
      setAiError('Please select a department first.');
      return;
    }
    setAiLoading(true);
    setAiError('');
    setAiSlots([]);
    setBookingSuccess('');
    try {
      const res = await appointmentAPI.getRecommendations({ department_id: aiDeptId, urgency: aiUrgency });
      const slots = (res.data.slots ?? []) as RecommendedSlot[];
      setAiSlots(slots);
      if (slots.length === 0) {
        setAiError('No available slots found for this department in the next 14 days.');
      }
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setAiError(typeof detail === 'string' ? detail : 'Failed to fetch recommendations.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleBookSlot = async (slot: RecommendedSlot) => {
    setBookingSlot(slot.doctor_id);
    setBookingSuccess('');
    setAiError('');
    try {
      await appointmentAPI.create({
        department_id: slot.department_id,
        doctor_id: slot.doctor_id,
        date: slot.date,
        time: slot.time,
        reason: '',
      });
      setBookingSuccess(`Appointment booked with ${slot.doctor_name} on ${slot.date} at ${slot.time}`);
      fetchAppointments();
      setAiSlots(prev => prev.filter(s => !(s.doctor_id === slot.doctor_id && s.date === slot.date && s.time === slot.time)));
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setAiError(typeof detail === 'string' ? detail : 'Failed to book this slot.');
    } finally {
      setBookingSlot(null);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Appointments</h2>
        <p className="text-muted-foreground">{isPatient ? 'Manage and book your medical appointments.' : 'Review appointments scheduled with you.'}</p>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />{error}
        </div>
      )}

      <div className="flex space-x-2 border-b">
        {(isPatient ? (['my', 'book', 'ai'] as const) : (['my'] as const)).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium text-sm transition-colors border-b-2 ${
              activeTab === tab ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'my' ? 'My Appointments' : tab === 'book' ? 'Book New' : (
              <span className="flex items-center gap-1"><Sparkles size={14} />AI Recommendations</span>
            )}
          </button>
        ))}
      </div>

      {/* My Appointments */}
      {activeTab === 'my' && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Doctor</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Date &amp; Time</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {appointmentsLoading ? (
                  <TableRow><TableCell colSpan={5} className="text-center py-8 text-gray-500">Loading appointments…</TableCell></TableRow>
                ) : appointments.length === 0 ? (
                  <TableRow><TableCell colSpan={5} className="text-center py-8 text-gray-500">No appointments found.</TableCell></TableRow>
                ) : (
                  appointments.map(apt => (
                    <TableRow key={apt.id}>
                      <TableCell className="font-medium"><div className="flex items-center"><User size={16} className="mr-2 text-gray-400"/>{apt.doctor?.full_name}</div></TableCell>
                      <TableCell>{apt.department?.name}</TableCell>
                      <TableCell>
                        <div className="flex flex-col text-sm">
                          <span className="flex items-center"><Calendar size={14} className="mr-1"/>{formatDate(apt.appointment_date)}</span>
                          <span className="flex items-center text-gray-500"><Clock size={14} className="mr-1"/>{formatTime(apt.appointment_time)}</span>
                        </div>
                      </TableCell>
                      <TableCell><Badge variant={getStatusColor(apt.status)}>{apt.status}</Badge></TableCell>
                      <TableCell>
                        {isPatient && apt.status === 'scheduled' && (
                          <Button variant="danger" size="sm" onClick={() => handleCancel(apt.id)}>Cancel</Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Book New */}
      {activeTab === 'book' && isPatient && (
        <Card className="max-w-2xl">
          <CardHeader><CardTitle>Book an Appointment</CardTitle></CardHeader>
          <CardContent>
            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm mb-4">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />{error}
              </div>
            )}
            <form onSubmit={handleBook} className="space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium">Department</label>
                <div className="relative">
                  <Building className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                  <select
                    className="w-full pl-10 pr-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                    value={form.department_id}
                    onChange={e => { setForm({...form, department_id: e.target.value, doctor_id: ''}); setDoctors([]); setError(''); }}
                    required
                  >
                    <option value="">Select Department</option>
                    {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">Doctor</label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                  <select
                    className="w-full pl-10 pr-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    value={form.doctor_id}
                    onChange={e => setForm({...form, doctor_id: e.target.value})}
                    disabled={!form.department_id}
                    required
                  >
                    <option value="">Select Doctor</option>
                    {doctors.map(d => <option key={d.id} value={d.id}>{d.full_name}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="Date" type="date" value={form.date} onChange={e => setForm({...form, date: e.target.value})} required />
                <Input label="Time" type="time" value={form.time} onChange={e => setForm({...form, time: e.target.value})} required />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">Reason for Visit</label>
                <textarea
                  className="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  value={form.reason}
                  onChange={e => setForm({...form, reason: e.target.value})}
                />
              </div>
              <Button type="submit" isLoading={loading} className="w-full">Confirm Booking</Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* AI Recommendations */}
      {activeTab === 'ai' && isPatient && (
        <div className="space-y-4 max-w-3xl">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Sparkles size={18} className="text-blue-500" />AI Appointment Recommendations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-gray-600">
                Select a department and urgency level. The AI will find the next available slots with real doctors, ranked by availability.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Department</label>
                  <div className="relative">
                    <Building className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                    <select
                      className="w-full pl-10 pr-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                      value={aiDeptId}
                      onChange={e => { setAiDeptId(e.target.value); setAiSlots([]); setAiError(''); setBookingSuccess(''); }}
                    >
                      <option value="">Select Department</option>
                      {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Urgency</label>
                  <select
                    className="w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500"
                    value={aiUrgency}
                    onChange={e => setAiUrgency(e.target.value as AppointmentRecommendationInput['urgency'])}
                  >
                    <option value="low">Low — routine checkup</option>
                    <option value="medium">Medium — non-urgent concern</option>
                    <option value="high">High — needs attention soon</option>
                    <option value="emergency">Emergency — urgent care needed</option>
                  </select>
                </div>
              </div>
              <Button onClick={handleGetRecommendations} isLoading={aiLoading} disabled={!aiDeptId}>
                <Sparkles size={16} className="mr-2" />Find Available Slots
              </Button>
            </CardContent>
          </Card>

          {aiError && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />{aiError}
            </div>
          )}

          {bookingSuccess && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md text-sm font-medium">
              ✓ {bookingSuccess}
            </div>
          )}

          {aiSlots.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Available Slots ({aiSlots.length})</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y">
                  {aiSlots.map((slot, i) => (
                    <div key={i} className="flex items-center justify-between p-4 hover:bg-gray-50">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <User size={14} className="text-gray-400" />
                          <span className="font-medium text-sm">{slot.doctor_name}</span>
                          {slot.specialization && (
                            <Badge variant="default">{slot.specialization}</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          <span className="flex items-center gap-1"><Calendar size={13} />{slot.date}</span>
                          <span className="flex items-center gap-1"><Clock size={13} />{slot.time}</span>
                          <span className="flex items-center gap-1"><Building size={13} />{slot.department_name}</span>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleBookSlot(slot)}
                        isLoading={bookingSlot === slot.doctor_id}
                      >
                        Book
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
