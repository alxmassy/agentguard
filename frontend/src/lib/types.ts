export type Decision = "ALLOW" | "BLOCK" | "REQUIRE_HUMAN_APPROVAL";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired";

export interface RiskFactors {
  action_weight: number;
  environment_weight: number;
  blast_radius_weight: number;
  reversibility_weight: number;
  privilege_weight: number;
}

export interface ParsedAction {
  tool: string;
  operation: string;
  action_type: string;
  is_destructive: boolean;
  is_read_only: boolean;
  raw_args?: string[];
  flags?: Record<string, any>;
  target_resource?: string | null;
}

export interface CommandInfo {
  raw: string;
  argv: string[];
}

export interface ActionRequest {
  request_id: string;
  environment: string;
  project_id: string;
  agent_id: string | null;
  original_task: string | null;
  command: CommandInfo;
  parsed_action: ParsedAction;
  decision: Decision;
  policy_id: string | null;
  risk_level: RiskLevel;
  risk_score: number;
  risk_factors: RiskFactors;
  created_at: string;
}

export interface Approval {
  id: string;
  request_id: string;
  status: ApprovalStatus;
  comment: string | null;
  approver_id?: string | null;
  created_at: string;
  resolved_at: string | null;
  action_requests: ActionRequest | null;
}

export interface AuditEvent {
  id: string;
  request_id: string;
  event_type: string;
  payload: Record<string, any>;
  occurred_at: string;
}

export interface PolicyRule {
  id: string;
  conditions: Record<string, any>;
  then: Decision;
  reason: string;
}

export interface DashboardStats {
  total_evaluations: number;
  allowed_count: number;
  blocked_count: number;
  require_approval_count: number;
  pending_approvals: number;
  critical_risk_count: number;
  high_risk_count: number;
  recent_actions: ActionRequest[];
}
