'use client';
import React from 'react';
import { useAuth } from '@/lib/auth';
import { Menu } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { getRoleColor } from '@/lib/utils';
import { usePathname } from 'next/navigation';

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const { user } = useAuth();
  const pathname = usePathname();
  const title = pathname.split('/').pop()?.replace('-', ' ') || 'Dashboard';

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-white px-4 shadow-sm sm:px-6">
      <div className="flex items-center">
        <button onClick={onMenuClick} className="mr-4 rounded-md p-1 text-gray-500 hover:bg-gray-100 lg:hidden">
          <Menu size={24} />
        </button>
        <h1 className="text-xl font-semibold capitalize text-gray-900">{title}</h1>
      </div>
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 border-l pl-4">
          <div className="text-sm font-medium text-gray-900">{user?.full_name || 'User'}</div>
          <Badge variant={getRoleColor(user?.role || '')}>{user?.role || 'Patient'}</Badge>
        </div>
      </div>
    </header>
  );
}
