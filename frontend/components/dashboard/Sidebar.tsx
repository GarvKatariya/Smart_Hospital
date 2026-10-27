'use client';
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import {
  LayoutDashboard, Users, Calendar, Activity, BedDouble,
  FileText, MessageSquare, Pill, TestTube, Stethoscope,
  LogOut, Settings, Hospital, Database
} from 'lucide-react';
import { cn } from '@/lib/utils';

export function Sidebar({ mobileOpen, setMobileOpen }: { mobileOpen: boolean, setMobileOpen: (v: boolean) => void }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const role = user?.role?.toLowerCase() || 'patient';

  const patientLinks = [
    { href: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { href: '/dashboard/symptoms', label: 'Symptom Checker', icon: <Activity size={20} /> },
    { href: '/dashboard/triage', label: 'AI Triage', icon: <Stethoscope size={20} /> },
    { href: '/dashboard/appointments', label: 'Appointments', icon: <Calendar size={20} /> },
    { href: '/dashboard/beds', label: 'Bed Availability', icon: <BedDouble size={20} /> },
    { href: '/dashboard/reports', label: 'Reports', icon: <FileText size={20} /> },
    { href: '/dashboard/prescriptions', label: 'Prescriptions', icon: <Pill size={20} /> },
    { href: '/dashboard/disease', label: 'Disease Risk', icon: <TestTube size={20} /> },
    { href: '/dashboard/chatbot', label: 'Chatbot', icon: <MessageSquare size={20} /> },
    { href: '/dashboard/profile', label: 'Profile', icon: <Settings size={20} /> },
  ];

  const doctorLinks = [
    { href: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { href: '/dashboard/appointments', label: 'Appointments', icon: <Calendar size={20} /> },
    { href: '/dashboard/beds', label: 'Bed Availability', icon: <BedDouble size={20} /> },
    { href: '/dashboard/reports', label: 'Reports', icon: <FileText size={20} /> },
    { href: '/dashboard/queue', label: 'Queue', icon: <Users size={20} /> },
    { href: '/dashboard/profile', label: 'Profile', icon: <Settings size={20} /> },
  ];

  const adminLinks = [
    { href: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { href: '/dashboard/admin/departments', label: 'Departments', icon: <Hospital size={20} /> },
    { href: '/dashboard/admin/doctors', label: 'Doctors', icon: <Users size={20} /> },
    { href: '/dashboard/admin/patients', label: 'Patients', icon: <Users size={20} /> },
    { href: '/dashboard/admin/audit', label: 'Audit History', icon: <FileText size={20} /> },
    { href: '/dashboard/appointments', label: 'Appointments', icon: <Calendar size={20} /> },
    { href: '/dashboard/beds', label: 'Beds', icon: <Activity size={20} /> },
    { href: '/dashboard/queue', label: 'Queue', icon: <Users size={20} /> },
    { href: '/dashboard/admin/models', label: 'AI Models', icon: <Database size={20} /> },
  ];

  const links = role === 'admin' ? adminLinks : role === 'doctor' ? doctorLinks : patientLinks;

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}
      <div className={cn(
        "fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-white border-r transition-transform lg:static lg:translate-x-0",
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex h-16 items-center px-6 border-b">
          <Hospital className="text-blue-600 mr-2" />
          <span className="font-bold text-xl text-gray-900">SmartHospital</span>
        </div>
        <div className="flex-1 overflow-y-auto py-4">
          <nav className="space-y-1 px-3">
            {links.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors",
                    active ? "bg-blue-50 text-blue-700" : "text-gray-700 hover:bg-gray-100"
                  )}
                >
                  <span className={cn("mr-3", active ? "text-blue-700" : "text-gray-400")}>{link.icon}</span>
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="p-4 border-t">
          <button
            onClick={logout}
            className="flex w-full items-center px-3 py-2.5 text-sm font-medium text-red-600 rounded-lg hover:bg-red-50"
          >
            <LogOut size={20} className="mr-3" />
            Logout
          </button>
        </div>
      </div>
    </>
  );
}
