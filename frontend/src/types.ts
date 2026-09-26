export type Ticket = {
  id: string;
  external_id: string;
  title: string;
  body: string;
  customer: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'open' | 'in_review' | 'reviewed';
  created_at: string;
};
export type Document = {
  id: string;
  title: string;
  content: string;
  source: string;
  created_at: string;
};
export type Citation = { document_id: string; title: string; excerpt: string; score: number };
export type Step = { name: string; status: string; detail: string; duration_ms: number };
export type Analysis = {
  id: string;
  ticket_id: string;
  summary: string;
  recommended_action: string;
  risk: 'low' | 'medium' | 'high';
  confidence: number;
  citations: Citation[];
  steps: Step[];
  draft_reply: string;
  needs_escalation: boolean;
  provider: string;
  latency_ms: number;
  created_at: string;
  action_id: string;
};
export type Action = {
  id: string;
  ticket_id: string;
  analysis_id: string;
  kind: string;
  status: 'pending' | 'approved' | 'rejected';
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  created_at: string;
  decided_at: string | null;
};
export type Audit = {
  id: string;
  event: string;
  entity_id: string;
  detail: Record<string, unknown>;
  created_at: string;
};
export type Evaluation = {
  id: string;
  total: number;
  passed: number;
  pass_rate: number;
  cases: Array<{
    id: string;
    name: string;
    passed: boolean;
    expected: string;
    actual: string;
    latency_ms: number;
  }>;
  created_at: string;
};
export type Workspace = { tenant: { id: string; name: string }; mode: string };
export type Metrics = {
  total_tickets: number;
  open_tickets: number;
  analyzed_tickets: number;
  pending_approvals: number;
  approved_actions: number;
  avg_latency_ms: number;
  grounded_rate: number;
};
export type ImportedTicket = Pick<
  Ticket,
  'external_id' | 'title' | 'body' | 'customer' | 'priority'
>;
