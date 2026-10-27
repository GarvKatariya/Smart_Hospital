import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor to add JWT token
api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor for 401 handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('hospital:session-expired'));
      }
    }
    return Promise.reject(error);
  }
);

export default api;

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  role: string;
  phone?: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  phone: string | null;
  is_active: boolean;
  created_at: string;
}

export interface UserProfileUpdate {
  full_name: string;
  phone: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export interface AppointmentInput {
  department_id: string;
  doctor_id: string;
  date: string;
  time: string;
  reason: string;
}

export interface AppointmentRecommendationInput {
  department_id: string;
  urgency: 'low' | 'medium' | 'high' | 'emergency';
}

export interface SymptomCheckInput {
  symptoms_text: string;
  selected_symptoms: string[];
}

export interface DiseasePredictionInput {
  age: number;
  sex: number;
  cp: number;
  trestbps: number;
  chol: number;
  fbs: number;
  restecg: number;
  thalach: number;
  exang: number;
  oldpeak: number;
  slope: number;
  ca: number;
  thal: number;
}

export interface TriageInput {
  symptoms: string;
  severity: number;
  duration: string;
  age: number;
  vital_signs: Record<string, number>;
  consciousness_level: string;
  red_flag_symptoms: string[];
}

export interface AdminDoctorInput {
  full_name: string;
  email: string;
  password: string;
  department_id: string;
  specialization?: string;
  qualification?: string;
  experience_years?: number;
}

export interface AdminPatient {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  actor_name: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string | null;
}

export const adminAPI = {
  getStats: () => api.get('/api/admin/stats'),
  getModelStatus: () => api.get('/api/admin/models'),
  getDoctors: () => api.get('/api/admin/doctors'),
  listDoctors: () => api.get('/api/admin/doctors'),
  createDoctor: (data: AdminDoctorInput) => api.post('/api/admin/doctors', data),
  getPatients: (skip = 0, limit = 50) => api.get<{ total: number; patients: AdminPatient[] }>('/api/admin/patients', { params: { skip, limit } }),
  getAuditLogs: (skip = 0, limit = 50) => api.get<{ total: number; logs: AuditLogEntry[] }>('/api/admin/audit-logs', { params: { skip, limit } }),
};

// API functions for each module
export const authAPI = {
  login: (email: string, password: string) => api.post('/api/auth/login', { email, password }),
  register: (data: RegisterData) => api.post('/api/auth/register', data),
  getMe: () => api.get('/api/auth/me'),
  updateProfile: (data: UserProfileUpdate) => api.patch('/api/auth/me', data),
  changePassword: (data: PasswordChange) => api.post('/api/auth/me/password', data),
};

export const departmentAPI = {
  list: () => api.get('/api/departments/'),
  listAll: () => api.get('/api/departments/admin/all'),
  get: (id: string) => api.get(`/api/departments/${id}`),
  create: (data: DepartmentInput) => api.post('/api/departments/', data),
  update: (id: string, data: DepartmentInput) => api.put(`/api/departments/${id}`, data),
};

export interface DepartmentInput {
  name: string;
  description: string;
  floor: string;
  phone: string;
  is_active: boolean;
}

export const doctorAPI = {
  list: (departmentId?: string) => api.get('/api/doctors/', { params: { department_id: departmentId } }),
  get: (id: string) => api.get(`/api/doctors/${id}`),
  getSchedule: (id: string) => api.get(`/api/doctors/${id}/schedule`),
  getMyStats: () => api.get('/api/doctors/me/stats'),
};

export const appointmentAPI = {
  list: () => api.get('/api/appointments/'),
  create: (data: AppointmentInput) => api.post('/api/appointments/', data),
  cancel: (id: string) => api.put(`/api/appointments/${id}/cancel`),
  getRecommendations: (data: AppointmentRecommendationInput) => api.post('/api/appointments/recommend', data),
};

export const symptomAPI = {
  check: (data: SymptomCheckInput) => api.post('/api/symptoms/check', data),
  list: () => api.get('/api/symptoms/'),
};

export const diseaseAPI = {
  predict: (data: DiseasePredictionInput) => api.post('/api/disease/predict', data),
};

export const reportAPI = {
  upload: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/api/reports/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); },
  get: (id: string) => api.get(`/api/reports/${id}`),
  summarize: (id: string) => api.post(`/api/reports/${id}/summarize`),
};

export const chatAPI = {
  createSession: () => api.post('/api/chat/sessions'),
  listSessions: () => api.get('/api/chat/sessions'),
  getMessages: (sessionId: string) => api.get(`/api/chat/sessions/${sessionId}/messages`),
  sendMessage: (sessionId: string, message: string) => api.post(`/api/chat/sessions/${sessionId}/messages`, { message }),
};

export const prescriptionAPI = {
  analyze: (file: File) => { const fd = new FormData(); fd.append('file', file); return api.post('/api/prescriptions/analyze', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); },
  get: (id: string) => api.get(`/api/prescriptions/${id}`),
};

export const bedAPI = {
  getCurrent: () => api.get('/api/beds/status'),
  getForecast: () => api.get('/api/beds/forecast'),
  getInventory: () => api.get<BedInventoryItem[]>('/api/beds/inventory'),
  updateStatus: (id: string, status: BedInventoryItem['status']) =>
    api.patch(`/api/beds/inventory/${id}`, { status }),
};

export interface BedInventoryItem {
  id: string;
  department_id: string;
  department_name: string;
  bed_number: string;
  bed_type: string | null;
  status: 'available' | 'occupied' | 'maintenance' | 'reserved';
}

export const triageAPI = {
  predict: (data: TriageInput) => api.post('/api/triage/predict', data),
  getQueue: () => api.get('/api/triage/queue'),
  updateQueueStatus: (id: string, status: 'in_progress' | 'completed' | 'cancelled') =>
    api.patch(`/api/triage/queue/${id}`, { status }),
};
