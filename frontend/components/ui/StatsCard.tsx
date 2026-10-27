import React from 'react';
import { Card, CardContent } from './Card';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  colorClass?: string;
}

export function StatsCard({ title, value, icon, trend, trendDirection, colorClass = 'text-blue-600' }: StatsCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <h4 className="mt-2 text-3xl font-bold">{value}</h4>
          </div>
          <div className={cn("rounded-full bg-gray-100 p-3", colorClass)}>{icon}</div>
        </div>
        {trend && (
          <div className="mt-4 flex items-center text-sm">
            <span className={cn(
              "font-medium",
              trendDirection === 'up' ? "text-green-600" : trendDirection === 'down' ? "text-red-600" : "text-gray-500"
            )}>
              {trend}
            </span>
            <span className="ml-2 text-gray-500">vs last month</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
