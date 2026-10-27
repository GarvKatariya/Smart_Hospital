'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity, ArrowRight, Calendar, Clock, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { StatsCard } from '@/components/ui/StatsCard';
import { useAuth } from '@/lib/auth';
import { appointmentAPI, doctorAPI } from '@/lib/api';

interface DoctorStats {
  appointments_today: number;
  pending_reports: number;
  total_patients: number;
}

interface AppointmentPreview {
  id: string;
  appointment_date: string;
  appointment_time: string;
  status: string;
  doctor?: { full_name: string };
  department?: { name: string };
}

export default function DashboardPage() {
  const { user } = useAuth();
  const role = user?.role?.toLowerCase() || 'patient';
  const [doctorStats, setDoctorStats] = useState<DoctorStats | null>(null);
  const [upcoming, setUpcoming] = useState<AppointmentPreview[]>([]);

  useEffect(() => {
    if (role === 'doctor') {
      doctorAPI.getMyStats().then(response => setDoctorStats(response.data)).catch(console.error);
    } else if (role === 'patient') {
      appointmentAPI.list().then(response => {
        const now = new Date();
        const items = response.data as AppointmentPreview[];
        setUpcoming(items
          .filter(item => item.status === 'scheduled' && new Date(item.appointment_date) >= now)
          .slice(0, 3));
      }).catch(console.error);
    }
  }, [role]);

  if (role === 'admin') {
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Hospital Administration</h2>
          <p className="text-muted-foreground">Open the live administration overview for current hospital statistics.</p>
        </div>
        <Link href="/dashboard/admin" className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700">
          Administration overview <ArrowRight size={16} className="ml-2" />
        </Link>
      </div>
    );
  }

  if (role === 'doctor') {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Dr. {user?.full_name}</h2>
          <p className="text-muted-foreground">Your schedule and patient overview for today.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <StatsCard title="Appointments Today" value={doctorStats ? String(doctorStats.appointments_today) : '…'} icon={<Calendar className="h-6 w-6 text-blue-600" />} />
          <StatsCard title="Pending Reports" value={doctorStats ? String(doctorStats.pending_reports) : '…'} icon={<Activity className="h-6 w-6 text-orange-600" />} colorClass="text-orange-600" />
          <StatsCard title="Total Patients" value={doctorStats ? String(doctorStats.total_patients) : '…'} icon={<Users className="h-6 w-6 text-green-600" />} colorClass="text-green-600" />
        </div>
        <Link href="/dashboard/appointments" className="inline-flex items-center text-blue-700 hover:underline">
          View your appointments <ArrowRight size={16} className="ml-2" />
        </Link>
      </div>
    );
  }

  const actions = [
    { title: 'Check Symptoms', href: '/dashboard/symptoms', icon: <Activity className="h-6 w-6 text-blue-600" />, color: 'bg-blue-100' },
    { title: 'Book Appointment', href: '/dashboard/appointments', icon: <Calendar className="h-6 w-6 text-green-600" />, color: 'bg-green-100' },
    { title: 'AI Chatbot', href: '/dashboard/chatbot', icon: <Clock className="h-6 w-6 text-purple-600" />, color: 'bg-purple-100' },
    { title: 'Upload Report', href: '/dashboard/reports', icon: <Users className="h-6 w-6 text-orange-600" />, color: 'bg-orange-100' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Welcome back, {user?.full_name}</h2>
        <p className="text-muted-foreground">Here&apos;s your health dashboard and quick actions.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {actions.map(action => (
          <Link key={action.href} href={action.href}>
            <Card className="h-full cursor-pointer transition-all hover:border-blue-500 hover:shadow-md">
              <CardContent className="flex flex-col items-center justify-center space-y-4 p-6 text-center">
                <div className={`rounded-full p-4 ${action.color}`}>{action.icon}</div>
                <h3 className="font-semibold">{action.title}</h3>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-lg font-medium">Upcoming Appointments</CardTitle>
          <Link href="/dashboard/appointments" className="flex items-center text-sm text-blue-600 hover:underline">
            View all <ArrowRight size={16} className="ml-1" />
          </Link>
        </CardHeader>
        <CardContent>
          {upcoming.length === 0 ? (
            <div className="p-6 text-center text-gray-500">No upcoming appointments.</div>
          ) : upcoming.map(appointment => (
            <div key={appointment.id} className="flex flex-wrap items-center justify-between gap-2 border-b py-3 last:border-0">
              <div>
                <p className="font-medium">{appointment.doctor?.full_name ?? 'Doctor'}</p>
                <p className="text-sm text-gray-500">{appointment.department?.name ?? 'Department'}</p>
              </div>
              <p className="text-sm text-gray-600">{new Date(appointment.appointment_date).toLocaleDateString()} at {appointment.appointment_time}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
