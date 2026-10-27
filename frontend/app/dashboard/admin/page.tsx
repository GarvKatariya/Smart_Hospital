'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { StatsCard } from '@/components/ui/StatsCard';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { adminAPI } from '@/lib/api';
import {
  Users, Calendar, BedDouble, Activity, Stethoscope,
  Building, ArrowRight, RefreshCw, CheckCircle, XCircle
} from 'lucide-react';
import Link from 'next/link';

interface AdminStats {
  total_patients: number;
  total_doctors: number;
  appointments_today: number;
  available_beds: number;
  total_beds: number;
  occupancy_rate: number;
  total_appointments: number;
  scheduled_appointments: number;
  total_departments: number;
}

interface ModelStatus {
  name: string;
  display_name: string;
  version: string | null;
  artifact_present: boolean;
}

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [models, setModels] = useState<ModelStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [statsRes, modelsRes] = await Promise.all([
        adminAPI.getStats(),
        adminAPI.getModelStatus(),
      ]);
      setStats(statsRes.data);
      setModels(modelsRes.data?.models || []);
    } catch (cause: unknown) {
      const detail = axios.isAxiosError(cause) ? cause.response?.data?.detail : null;
      setError(typeof detail === 'string' ? detail : 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    Promise.all([adminAPI.getStats(), adminAPI.getModelStatus()])
      .then(([statsResponse, modelsResponse]) => {
        if (!active) return;
        setStats(statsResponse.data);
        setModels(modelsResponse.data?.models || []);
      })
      .catch(() => {
        if (active) setError('Failed to load admin data. Confirm your administrator access.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const quickLinks = [
    { title: 'Manage Doctors', href: '/dashboard/admin/doctors', icon: <Stethoscope className="h-6 w-6 text-blue-600" />, color: 'bg-blue-100', desc: 'Add or view doctors' },
    { title: 'Departments', href: '/dashboard/admin/departments', icon: <Building className="h-6 w-6 text-green-600" />, color: 'bg-green-100', desc: 'Department management' },
    { title: 'AI Models', href: '/dashboard/admin/models', icon: <Activity className="h-6 w-6 text-purple-600" />, color: 'bg-purple-100', desc: 'Model versions & status' },
    { title: 'Bed Management', href: '/dashboard/beds', icon: <BedDouble className="h-6 w-6 text-orange-600" />, color: 'bg-orange-100', desc: 'View bed occupancy' },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Hospital Administration</h2>
          <p className="text-muted-foreground">Overview of hospital operations and statistics.</p>
        </div>
        <Button variant="outline" onClick={fetchData} disabled={loading}>
          <RefreshCw size={16} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">{error}</div>
      )}

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Patients"
          value={loading ? '...' : String(stats?.total_patients ?? 0)}
          icon={<Users className="h-6 w-6 text-blue-600" />}
        />
        <StatsCard
          title="Total Doctors"
          value={loading ? '...' : String(stats?.total_doctors ?? 0)}
          icon={<Stethoscope className="h-6 w-6 text-green-600" />}
          colorClass="text-green-600"
        />
        <StatsCard
          title="Appointments Today"
          value={loading ? '...' : String(stats?.appointments_today ?? 0)}
          icon={<Calendar className="h-6 w-6 text-orange-600" />}
          colorClass="text-orange-600"
        />
        <StatsCard
          title="Available Beds"
          value={loading ? '...' : `${stats?.available_beds ?? 0}/${stats?.total_beds ?? 0}`}
          icon={<BedDouble className="h-6 w-6 text-purple-600" />}
          colorClass="text-purple-600"
        />
      </div>

      {/* Secondary stats */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-gray-500">Bed Occupancy Rate</p>
              <p className="text-2xl font-bold mt-1">{stats.occupancy_rate ?? 0}%</p>
              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${(stats.occupancy_rate ?? 0) > 85 ? 'bg-red-500' : (stats.occupancy_rate ?? 0) > 70 ? 'bg-yellow-500' : 'bg-green-500'}`}
                  style={{ width: `${Math.min(stats.occupancy_rate ?? 0, 100)}%` }}
                />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-gray-500">Total Appointments</p>
              <p className="text-2xl font-bold mt-1">{stats.total_appointments ?? 0}</p>
              <p className="text-xs text-gray-400 mt-1">{stats.scheduled_appointments ?? 0} scheduled</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-gray-500">Active Departments</p>
              <p className="text-2xl font-bold mt-1">{stats.total_departments ?? 0}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Quick Links */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Quick Actions</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {quickLinks.map((link, i) => (
            <Link key={i} href={link.href}>
              <Card className="hover:border-blue-500 hover:shadow-md transition-all cursor-pointer h-full">
                <CardContent className="flex flex-col items-center justify-center p-6 text-center space-y-3">
                  <div className={`p-3 rounded-full ${link.color}`}>{link.icon}</div>
                  <div>
                    <h3 className="font-semibold text-sm">{link.title}</h3>
                    <p className="text-xs text-gray-500 mt-1">{link.desc}</p>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {/* AI Models Status */}
      {models.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-lg">AI Model Status</CardTitle>
            <Link href="/dashboard/admin/models" className="text-sm text-blue-600 hover:underline flex items-center">
              View all <ArrowRight size={14} className="ml-1" />
            </Link>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {models.map(model => (
                <div key={model.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border">
                  <div>
                    <p className="text-sm font-medium">{model.display_name}</p>
                    {model.version && <p className="text-xs text-gray-500">v{model.version}</p>}
                  </div>
                  {model.artifact_present ? (
                    <Badge variant="success">
                      <CheckCircle size={12} className="mr-1" /> Ready
                    </Badge>
                  ) : (
                    <Badge variant="danger">
                      <XCircle size={12} className="mr-1" /> Missing
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
