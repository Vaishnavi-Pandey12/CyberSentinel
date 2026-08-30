export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type Role = 'LEA Officer' | 'Bank/FI' | 'I4C Analyst' | 'Admin';
export type AlertStatus = 'NEW' | 'ACKNOWLEDGED' | 'ACTIVE';

export interface User {
  id?: string;
  name: string;
  email: string;
  role: Role;
}

export interface Prediction {
  id: string;
  location_id: string;
  location_name: string;
  region: string;
  latitude: number;
  longitude: number;
  risk_score: number; // Stored/handled normalized 0-100 on frontend for UI display
  risk_level: RiskLevel;
  predicted_window: string;
  crime_category: string;
  rank: number;
  top_factors: string[];
  related_complaints: string[];
  model_version: string;
  confidence: number;
  case_id?: string;
  created_at?: string;
}

export interface Alert {
  id: string;
  prediction_id: string;
  severity: RiskLevel;
  status: AlertStatus;
  riskScore?: number;
  risk_score?: number;
  recipient_role?: string;
  created_at: string;
  acknowledged_at?: string | null;
}

export interface Case {
  id: string;
  status: 'ACTIVE' | 'PENDING' | 'CLOSED';
  summary: string;
  risk_level: RiskLevel;
  complaints: string[];
  hotspot_ids: string[];
  notes: string[];
  timeline: { time: string; event: string; location: string }[];
}

export interface DashboardSummary {
  totalComplaints: number;
  highRiskZones: number;
  activeAlerts: number;
  atRiskAtms: number;
  risk_level_breakdown?: Record<string, number>;
}

export interface Filters {
  region: string;
  category: string;
  window: string;
  risk: string;
}
