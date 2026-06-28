export type SignalType =
  | 'funding_round'
  | 'sdr_hiring'
  | 'growth_news'
  | 'upmarket_pivot'
  | string;

export type LeadTier = 'High' | 'Medium' | 'Low';
export type ICPFit = 'Strong' | 'Partial' | 'Poor';
export type LeadBadge = 'new_today' | 'score_up' | 'score_down' | 'signal_added' | 'filtered';

export interface ExtractedSignal {
  signal_type: SignalType;
  verbatim_quote: string;
  quote_validated: boolean;
  similarity_score: number;
  source_url?: string;
  recency_label: string;
  score_contribution: number;
}

export interface DNSAuditObjective {
  spf: string;
  dkim: string;
  dmarc: string;
  issues: string[];
}

export interface Contact {
  name: string;
  title: string;
  email: string;
  confidence: string;
  source?: string;
}

export interface ConfidenceEvaluation {
  label: string;
  color: string;
  verified: number;
  total: number;
}

export interface LeadDetailResponse {
  id: string;
  company_name: string;
  domain: string;
  industry: string;
  employee_count: number | null;
  funding_stage: string | null;
  intent_score: number;
  signal_freshness: number;
  tier: LeadTier;
  icp_fit: ICPFit;
  confidence: ConfidenceEvaluation;
  why_now: string;
  badge: LeadBadge | null;
  signals: ExtractedSignal[];
  ai_verdict: string;
  dns_audit: DNSAuditObjective;
  contacts?: Contact[];
  last_updated: string;
}
