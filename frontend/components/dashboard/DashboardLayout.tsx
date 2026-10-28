'use client';
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { LoadingSpinner } from '../ui/LoadingSpinner';

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace('/login');
      return;
    }
    if (!loading && user) {
      const role = user.role?.toLowerCase();
      const requiredRole = pathname.startsWith('/dashboard/admin') ? 'admin'
        : pathname === '/dashboard/queue' ? 'staff'
        : ['/dashboard/symptoms', '/dashboard/triage', '/dashboard/my-queue', '/dashboard/disease', '/dashboard/chatbot', '/dashboard/prescriptions'].includes(pathname) ? 'patient'
        : pathname === '/dashboard/reports' ? 'patient_or_doctor'
        : null;
      const permitted = requiredRole === null
        || (requiredRole === 'staff' ? ['admin', 'doctor'].includes(role || '')
          : requiredRole === 'patient_or_doctor' ? ['patient', 'doctor'].includes(role || '')
          : role === requiredRole);
      if (!permitted) router.replace('/dashboard');
    }
  }, [loading, isAuthenticated, router, pathname, user]);

  if (loading || !isAuthenticated) {
    return <div className="flex h-screen items-center justify-center"><LoadingSpinner size="lg" /></div>;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
