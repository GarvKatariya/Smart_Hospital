'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatsCard } from '@/components/ui/StatsCard';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '@/components/ui/Table';
import { Alert } from '@/components/ui/Alert';
import { bedAPI } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, BedDouble, Check } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import type { BedInventoryItem } from '@/lib/api';

interface BedDepartment {
  department_id: string;
  department?: { name: string };
  total_capacity: number;
  occupied: number;
  available: number;
  occupancy_rate: number;
}

interface BedForecast {
  dates: string[];
  predicted_occupied: number[];
  predicted_available: number[];
  current_occupied?: number;
  total_beds: number;
  source: string;
  model_note?: string | null;
  warnings: string[];
}

export default function BedsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [currentBeds, setCurrentBeds] = useState<BedDepartment[]>([]);
  const [inventory, setInventory] = useState<BedInventoryItem[]>([]);
  const [selectedBeds, setSelectedBeds] = useState<string[]>([]);
  const [targetStatus, setTargetStatus] = useState<BedInventoryItem['status']>('available');
  const [savingBeds, setSavingBeds] = useState(false);
  const [forecast, setForecast] = useState<BedForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      bedAPI.getCurrent().then(res => setCurrentBeds(Array.isArray(res.data) ? res.data : [])),
      bedAPI.getForecast().then(res => setForecast(res.data)),
      bedAPI.getInventory().then(res => setInventory(Array.isArray(res.data) ? res.data : [])),
    ])
      .catch(() => setError('Could not load bed information. Sign in and try again.'))
      .finally(() => setLoading(false));
  }, []);

  const refreshBedData = async () => {
    const [statusResponse, inventoryResponse, forecastResponse] = await Promise.all([
      bedAPI.getCurrent(), bedAPI.getInventory(), bedAPI.getForecast(),
    ]);
    setCurrentBeds(Array.isArray(statusResponse.data) ? statusResponse.data : []);
    setInventory(Array.isArray(inventoryResponse.data) ? inventoryResponse.data : []);
    setForecast(forecastResponse.data);
  };

  const toggleBedSelection = (bedId: string) => {
    setSelectedBeds(current => current.includes(bedId)
      ? current.filter(id => id !== bedId)
      : [...current, bedId]);
  };

  const saveBedStatuses = async () => {
    if (!selectedBeds.length) return;
    setSavingBeds(true);
    setError('');
    try {
      await Promise.all(selectedBeds.map(id => bedAPI.updateStatus(id, targetStatus)));
      setSelectedBeds([]);
      await refreshBedData();
    } catch {
      try { await refreshBedData(); } catch { /* Keep the original update error visible. */ }
      setError('Could not update the selected beds. Refresh and try again.');
    } finally {
      setSavingBeds(false);
    }
  };

  const bedsByDepartment = inventory.reduce<Record<string, BedInventoryItem[]>>((groups, bed) => {
    (groups[bed.department_name] ||= []).push(bed);
    return groups;
  }, {});

  const totalBeds = currentBeds.reduce((acc, b) => acc + (b.total_capacity || 0), 0);
  const totalOccupied = currentBeds.reduce((acc, b) => acc + (b.occupied || 0), 0);
  const totalAvailable = currentBeds.reduce((acc, b) => acc + (b.available || 0), 0);
  const occupancyRate = totalBeds > 0 ? (totalOccupied / totalBeds) * 100 : 0;

  const highOccupancyDepts = currentBeds.filter(
    b => b.total_capacity > 0 && (b.occupied / b.total_capacity) > 0.9
  );

  // Anchor the forecast to today's live bed count so the model's future
  // values can be compared directly with current occupancy.
  const forecastChartData = forecast
    ? [
        {
          date: 'Today',
          actual: forecast.current_occupied ?? totalOccupied,
          predicted: forecast.current_occupied ?? totalOccupied,
        },
        ...(forecast.dates || []).map((d, i) => ({
          date: d,
          actual: null,
          predicted: forecast.predicted_occupied?.[i] ?? 0,
        })),
      ]
    : [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Bed Availability &amp; Forecast</h2>
        <p className="text-muted-foreground">Monitor and predict hospital bed occupancy.</p>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {highOccupancyDepts.length > 0 && (
        <Alert variant="warning" title="High Occupancy Alert">
          The following departments are at critical capacity:{' '}
          {highOccupancyDepts.map(d => d.department?.name).join(', ')}.
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard title="Total Beds" value={loading ? '...' : totalBeds} icon={<BedDouble className="h-6 w-6 text-blue-600" />} />
        <StatsCard title="Occupied" value={loading ? '...' : totalOccupied} icon={<Activity className="h-6 w-6 text-red-600" />} colorClass="text-red-600 bg-red-100" />
        <StatsCard title="Available" value={loading ? '...' : totalAvailable} icon={<BedDouble className="h-6 w-6 text-green-600" />} colorClass="text-green-600 bg-green-100" />
        <StatsCard title="Occupancy Rate" value={loading ? '...' : `${occupancyRate.toFixed(1)}%`} icon={<Activity className="h-6 w-6 text-purple-600" />} colorClass="text-purple-600 bg-purple-100" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Department Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {!loading && currentBeds.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No bed data available. Beds may not be configured yet.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Department</TableHead>
                    <TableHead>Capacity</TableHead>
                    <TableHead>Occupied</TableHead>
                    <TableHead>Available</TableHead>
                    <TableHead>Utilization</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentBeds.map(b => {
                    const util = b.total_capacity > 0 ? (b.occupied / b.total_capacity) * 100 : 0;
                    return (
                      <TableRow key={b.department_id}>
                        <TableCell className="font-medium">{b.department?.name || 'Unknown'}</TableCell>
                        <TableCell>{b.total_capacity}</TableCell>
                        <TableCell>{b.occupied}</TableCell>
                        <TableCell>{b.available}</TableCell>
                        <TableCell>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${util > 90 ? 'bg-red-500' : util > 75 ? 'bg-yellow-500' : 'bg-green-500'}`}
                              style={{ width: `${Math.min(util, 100)}%` }}
                            />
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Occupancy Trend &amp; 7-Day Forecast</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            {forecast ? (
              <>
              <p className="mb-2 text-xs text-gray-500">Starting from today&apos;s live count · Forecast source: {forecast.source}</p>
              {forecast.model_note && (
                <p className="mb-2 text-xs text-amber-700">{forecast.model_note}</p>
              )}
              <ResponsiveContainer width="100%" height="90%">
                <LineChart data={forecastChartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={value => value === 'Today' ? value : new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} />
                  <YAxis domain={[0, Math.max(forecast.total_beds, 1)]} allowDecimals={false} />
                  <Tooltip labelFormatter={value => value === 'Today' ? 'Today · live inventory' : new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { dateStyle: 'medium' })} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="#16a34a"
                    strokeWidth={3}
                    dot={{ r: 5 }}
                    connectNulls={false}
                    name="Live occupancy"
                  />
                  <Line
                    type="monotone"
                    dataKey="predicted"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    dot={{ r: 4 }}
                    name="Forecast occupancy"
                  />
                </LineChart>
              </ResponsiveContainer>
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                {loading ? 'Loading forecast...' : 'Forecast unavailable'}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Bed Map</CardTitle>
          <p className="text-sm text-muted-foreground">
            {isAdmin
              ? 'Select one or more beds, choose a status, then apply the change.'
              : 'Read-only bed status by department. Contact an administrator to change availability.'}
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {isAdmin && (
            <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-gray-50 p-4">
              <span className="text-sm font-medium">{selectedBeds.length} bed{selectedBeds.length === 1 ? '' : 's'} selected</span>
              <select
                aria-label="Set selected bed status"
                value={targetStatus}
                onChange={event => setTargetStatus(event.target.value as BedInventoryItem['status'])}
                className="h-10 rounded-md border bg-white px-3 text-sm"
              >
                <option value="available">Available</option>
                <option value="occupied">Occupied</option>
                <option value="reserved">Reserved</option>
                <option value="maintenance">Maintenance</option>
              </select>
              <Button onClick={() => void saveBedStatuses()} disabled={!selectedBeds.length || savingBeds} isLoading={savingBeds}>
                <Check size={16} className="mr-2" />Apply status
              </Button>
              <Button variant="outline" onClick={() => setSelectedBeds([])} disabled={!selectedBeds.length || savingBeds}>Clear selection</Button>
            </div>
          )}

          <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-gray-600">
            {([
              ['available', 'Available'], ['occupied', 'Occupied'],
              ['reserved', 'Reserved'], ['maintenance', 'Maintenance'],
            ] as const).map(([status, label]) => (
              <span key={status} className="inline-flex items-center gap-2">
                <span className={`h-3 w-3 rounded-sm ${status === 'available' ? 'bg-emerald-500' : status === 'occupied' ? 'bg-rose-500' : status === 'reserved' ? 'bg-amber-400' : 'bg-slate-400'}`} />
                {label}
              </span>
            ))}
          </div>

          {loading ? <p className="py-6 text-center text-sm text-gray-500">Loading bed map…</p> : inventory.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-500">No individual beds are configured.</p>
          ) : Object.entries(bedsByDepartment).map(([department, beds]) => (
            <section key={department} className="space-y-3">
              <h3 className="font-semibold">{department}<span className="ml-2 text-sm font-normal text-gray-500">{beds.length} beds</span></h3>
              <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 md:grid-cols-7 lg:grid-cols-9">
                {beds.map(bed => {
                  const selected = selectedBeds.includes(bed.id);
                  const statusColor = bed.status === 'available' ? 'border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                    : bed.status === 'occupied' ? 'border-rose-300 bg-rose-50 text-rose-800'
                    : bed.status === 'reserved' ? 'border-amber-300 bg-amber-50 text-amber-800'
                    : 'border-slate-300 bg-slate-100 text-slate-700';
                  return (
                    <button
                      key={bed.id}
                      type="button"
                      disabled={!isAdmin}
                      onClick={() => toggleBedSelection(bed.id)}
                      aria-pressed={isAdmin ? selected : undefined}
                      title={`${bed.bed_number} · ${bed.bed_type || 'bed'} · ${bed.status}`}
                      className={`min-h-16 rounded-lg border p-2 text-left transition ${statusColor} ${isAdmin ? 'cursor-pointer' : 'cursor-default'} ${selected ? 'ring-2 ring-blue-600 ring-offset-1' : ''}`}
                    >
                      <span className="block text-sm font-semibold">{bed.bed_number}</span>
                      <span className="block text-xs capitalize">{bed.status.replace('_', ' ')}</span>
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
