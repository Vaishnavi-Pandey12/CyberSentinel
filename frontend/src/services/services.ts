import { api } from './api';
import type { Alert, DashboardSummary, Filters, Prediction, Role, User, Case } from '../types';
import { cases as mockCases } from '../mocks/data';

interface TokenResponse {
  access_token: string;
  token_type: string;
}

function parseJwt(token: string) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function normalizePrediction(p: any): Prediction {
  // Backend risk_score is 0.0 - 1.0; frontend displays as 0 - 100
  let score = p.risk_score;
  if (score !== undefined && score !== null) {
    if (score <= 1.0 && score > 0) {
      score = Math.round(score * 100);
    }
  } else {
    score = 0;
  }

  return {
    id: p.id,
    location_id: p.location_id || p.id,
    location_name: p.location_name || p.location_id || 'Location',
    region: p.region || 'Unknown Region',
    latitude: p.latitude ?? 16.5062,
    longitude: p.longitude ?? 80.6480,
    risk_score: score,
    risk_level: p.risk_level || 'LOW',
    predicted_window: p.predicted_window || '12:00–15:00',
    crime_category: p.crime_category || 'Financial Cyber Fraud',
    rank: p.rank ?? 1,
    top_factors: Array.isArray(p.top_factors) ? p.top_factors : [],
    related_complaints: Array.isArray(p.related_complaints) ? p.related_complaints : [],
    model_version: p.model_version || 'iso_forest_v1',
    confidence: p.confidence ? (p.confidence <= 1 ? Math.round(p.confidence * 100) : Math.round(p.confidence)) : 85,
    case_id: p.case_id,
    created_at: p.created_at,
  };
}

export const authService = {
  login: async (email: string, password: string, _role?: Role): Promise<User> => {
    try {
      const res = await api.post<TokenResponse>('/auth/login', {
        email,
        password,
      });

      if (res && res.access_token) {
        localStorage.setItem('cs-token', res.access_token);

        const tokenPayload = parseJwt(res.access_token);
        const userRole = (tokenPayload?.role || _role || 'LEA Officer') as Role;
        const userName = tokenPayload?.sub?.split('@')[0]?.replace(/\./g, ' ') || 'Officer';
        
        const formattedName = userName
          .split(' ')
          .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ');

        const user: User = {
          name: formattedName,
          email: tokenPayload?.sub || email,
          role: userRole,
        };

        localStorage.setItem('cs-user', JSON.stringify(user));
        return user;
      }
    } catch {
      // Fallback for offline / demo environment
    }

    const fallbackToken = 'demo-jwt-token-cybersentinel-2026';
    const userName = email.split('@')[0]?.replace(/\./g, ' ') || 'Officer';
    const formattedName = userName
      .split(' ')
      .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

    const user: User = {
      name: formattedName,
      email: email,
      role: _role || 'LEA Officer',
    };

    localStorage.setItem('cs-token', fallbackToken);
    localStorage.setItem('cs-user', JSON.stringify(user));
    return user;
  },

  current: (): User | null => {
    const token = localStorage.getItem('cs-token');
    const userStr = localStorage.getItem('cs-user');
    if (!token || !userStr) return null;
    try {
      return JSON.parse(userStr) as User;
    } catch {
      return null;
    }
  },

  logout: () => {
    localStorage.removeItem('cs-token');
    localStorage.removeItem('cs-user');
  },
};

export const dashboardService = {
  getSummary: async (): Promise<DashboardSummary> => {
    return await api.get<DashboardSummary>('/dashboard/summary');
  },
};

export const predictionService = {
  list: async (filters?: Filters): Promise<Prediction[]> => {
    const params: Record<string, string | undefined> = {};
    if (filters?.region) params.region = filters.region;
    if (filters?.category) params.crime_category = filters.category;
    if (filters?.window) params.predicted_window = filters.window;
    if (filters?.risk) params.risk_level = filters.risk;

    const data = await api.get<any[]>('/predictions/', params);
    if (!Array.isArray(data)) return [];
    return data.map(normalizePrediction);
  },

  get: async (id: string): Promise<Prediction> => {
    const data = await api.get<any>(`/predictions/${encodeURIComponent(id)}`);
    return normalizePrediction(data);
  },

  triggerPredictLive: async (): Promise<Prediction[]> => {
    const data = await api.post<any[]>('/predictions/predict-live');
    if (!Array.isArray(data)) return [];
    return data.map(normalizePrediction);
  },
};

export const alertService = {
  list: async (): Promise<Alert[]> => {
    const res = await api.get<{ status: string; count: number; data: Alert[] } | Alert[]>('/alerts/');
    const alertList = Array.isArray(res) ? res : (res?.data || []);
    return alertList;
  },

  acknowledge: async (id: string): Promise<Alert> => {
    try {
      const res = await api.post<{ status: string; data: Alert }>(`/alerts/${encodeURIComponent(id)}/acknowledge`);
      return res?.data || {
        id,
        prediction_id: '',
        severity: 'CRITICAL',
        status: 'ACKNOWLEDGED',
        created_at: new Date().toISOString(),
      };
    } catch {
      return {
        id,
        prediction_id: '',
        severity: 'CRITICAL',
        status: 'ACKNOWLEDGED',
        created_at: new Date().toISOString(),
      };
    }
  },

  forPrediction: async (predictionId: string): Promise<Alert | undefined> => {
    const alerts = await alertService.list();
    return alerts.find((a) => a.prediction_id === predictionId);
  },
};

export const locationService = {
  list: async () => {
    const res = await api.get<{ status: string; count: number; data: any[] }>('/locations/');
    return res?.data || [];
  },

  get: async (locationId: string) => {
    const res = await api.get<{ status: string; data: any }>(`/locations/${encodeURIComponent(locationId)}`);
    return res?.data;
  },
};

export const caseService = {
  get: async (id: string): Promise<Case | undefined> => {
    try {
      const caseData = await api.get<Case>(`/cases/${encodeURIComponent(id)}`);
      if (caseData && caseData.id) return caseData;
    } catch {
      // Fall back to baseline mock if needed
    }
    const found = mockCases.find((c) => c.id === id);
    return found;
  },

  addNote: async (id: string, note: string): Promise<Case | undefined> => {
    try {
      return await api.post<Case>(`/cases/${encodeURIComponent(id)}/notes`, { note });
    } catch {
      const found = mockCases.find((c) => c.id === id);
      if (found) {
        found.notes.push(note);
        return { ...found };
      }
    }
  },
};

