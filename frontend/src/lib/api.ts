import type { LeadDetailResponse } from '../types/lead';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

export interface PitcherModeResponse {
  lead_id: string;
  subject_line: string;
  email_body: string;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export function fetchLeads(): Promise<LeadDetailResponse[]> {
  return requestJson<LeadDetailResponse[]>('/api/leads/');
}

export function fetchPitcherMode(id: string): Promise<PitcherModeResponse> {
  return requestJson<PitcherModeResponse>(`/api/leads/${id}/verdict`, {
    method: 'POST',
  });
}

export function ingestLead(companyName: string): Promise<LeadDetailResponse> {
  return requestJson<LeadDetailResponse>('/api/leads/ingest', {
    method: 'POST',
    body: JSON.stringify({ company_name: companyName }),
  });
}

export function deleteLead(id: string): Promise<{ status: string; id: string }> {
  return requestJson<{ status: string; id: string }>(`/api/leads/${id}`, {
    method: 'DELETE',
  });
}

export interface PipelineStatusResponse {
  last_run_time: string;
  lead_count_processed: number;
  status: string;
  errors_encountered: boolean;
}

export function fetchPipelineStatus(): Promise<PipelineStatusResponse> {
  return requestJson<PipelineStatusResponse>('/api/pipeline/status');
}
