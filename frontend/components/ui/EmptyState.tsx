import React from 'react';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 p-8 text-center bg-gray-50/50", className)}>
      <div className="mb-4 text-gray-400">{icon}</div>
      <h3 className="mb-1 text-lg font-semibold text-gray-900">{title}</h3>
      {description && <p className="mb-4 text-sm text-gray-500 max-w-sm">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}
