import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString();
}

export function formatTime(timeStr: string) {
  if (!timeStr) return '';
  return new Date(`1970-01-01T${timeStr}`).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function getRoleColor(role: string): 'danger' | 'info' | 'success' | 'default' {
  switch (role.toLowerCase()) {
    case 'admin': return 'danger';
    case 'doctor': return 'info';
    case 'patient': return 'success';
    default: return 'default';
  }
}

export function getUrgencyColor(urgency: string): 'danger' | 'warning' | 'success' | 'default' {
  switch (urgency.toLowerCase()) {
    case 'high': return 'danger';
    case 'medium': return 'warning';
    case 'low': return 'success';
    default: return 'default';
  }
}

export function getStatusColor(status: string): 'success' | 'warning' | 'danger' | 'default' {
  switch (status.toLowerCase()) {
    case 'completed': return 'success';
    case 'pending': return 'warning';
    case 'cancelled': return 'danger';
    default: return 'default';
  }
}
