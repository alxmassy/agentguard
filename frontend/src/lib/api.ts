import { ActionRequest, Approval, AuditEvent, DashboardStats, PolicyRule } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function fetchStats(): Promise<DashboardStats> {
  const res = await fetch(`${BASE}/api/v1/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function fetchApprovals(status?: string): Promise<Approval[]> {
  const url = status && status !== "all" 
    ? `${BASE}/api/v1/approvals?status=${status}` 
    : `${BASE}/api/v1/approvals`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch approvals");
  const data = await res.json();
  return data.approvals || [];
}

export async function approveRequest(id: string, comment?: string) {
  const res = await fetch(`${BASE}/api/v1/approvals/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment: comment || "Approved via Dashboard" }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to approve request");
  }
  return res.json();
}

export async function rejectRequest(id: string, reason: string) {
  const res = await fetch(`${BASE}/api/v1/approvals/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason || "Rejected by human reviewer" }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to reject request");
  }
  return res.json();
}

export async function fetchActions(
  environment?: string,
  decision?: string,
  limit: number = 50,
  offset: number = 0
): Promise<{ actions: ActionRequest[]; total: number }> {
  const params = new URLSearchParams();
  if (environment && environment !== "all") params.append("environment", environment);
  if (decision && decision !== "all") params.append("decision", decision);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());

  const res = await fetch(`${BASE}/api/v1/actions?${params.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch actions");
  return res.json();
}

export async function fetchActionDetail(requestId: string): Promise<ActionRequest> {
  const res = await fetch(`${BASE}/api/v1/actions/${requestId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch action detail");
  return res.json();
}

export async function fetchAuditEvents(requestId?: string): Promise<AuditEvent[]> {
  const url = requestId ? `${BASE}/api/v1/audit?request_id=${requestId}` : `${BASE}/api/v1/audit`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch audit events");
  const data = await res.json();
  return data.events || [];
}

export async function fetchPolicies(): Promise<{ rules: PolicyRule[]; default: string; count: number }> {
  const res = await fetch(`${BASE}/api/v1/policies`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch policies");
  return res.json();
}

export async function seedDemoData(): Promise<any> {
  const res = await fetch(`${BASE}/api/v1/demo/seed`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to seed demo data");
  return res.json();
}

export async function checkHealth(): Promise<{ status: string; storage_mode: string; db_available: boolean }> {
  const res = await fetch(`${BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}
