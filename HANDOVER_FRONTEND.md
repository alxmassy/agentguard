# AgentGuard — Frontend Handover

> **Read this entire document before writing a single line of code.**

---

## What is AgentGuard?

AgentGuard is a **runtime safety layer** that sits between an AI agent and the infrastructure it controls. Before an agent runs a dangerous command (e.g., `terraform destroy`, `DROP TABLE`), it calls AgentGuard's backend. The backend evaluates the command and either:
- **ALLOWs** it → runs immediately
- **BLOCKs** it → never runs
- **REQUIRES HUMAN APPROVAL** → CLI hangs, waiting for a human to approve/reject via the dashboard

**Your job is to build that dashboard.**

---

## Stack decision

| Layer | Technology |
|---|---|
| Framework | **Next.js 15** (App Router) |
| Styling | **Tailwind CSS** |
| Components | **shadcn/ui** |
| Data fetching | `fetch` with SWR for polling/live updates |
| Auth | **Supabase Auth** (JS client) — wait for backend auth milestone before wiring |
| Language | **TypeScript** (strict mode) |

> **Why this stack?** It matches the design doc (§29 repo structure specifies Next.js + Tailwind + shadcn/ui) and Supabase has a first-class JS SDK.

---

## Setup

```bash
git clone https://github.com/alxmassy/agentguard.git
cd agentguard/frontend

# The frontend/ directory is empty — you initialize it
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Add shadcn/ui
npx shadcn@latest init

# Add Supabase JS client
npm install @supabase/supabase-js
```

**Environment variables** — create `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://nxthzjioglyjlbqysaho.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<get from Alex — the anon/public key, not the service key>
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> **Important:** Never use the service role key in the frontend. Only the anon key.

---

## The backend API (all endpoints are live and ready)

The backend is running at `http://localhost:8000` (dev). All these endpoints already exist:

### Approvals
```
GET  /api/v1/approvals?status=pending   → list approvals
GET  /api/v1/approvals/{id}             → single approval detail
POST /api/v1/approvals/{id}/approve     → body: {"comment": "LGTM"}
POST /api/v1/approvals/{id}/reject      → body: {"reason": "Wrong environment"}
```

### Actions
```
POST /api/v1/actions/evaluate           → (called by CLI, not dashboard)
GET  /api/v1/actions/{id}              → full detail for one action
```

### Health
```
GET  /health                            → {"status": "healthy", "db_available": true}
```

**Approval object shape:**
```typescript
interface Approval {
  id: string;                    // UUID
  request_id: string;            // "AG-xxxxxxxx"
  status: "pending" | "approved" | "rejected" | "expired";
  comment: string | null;
  created_at: string;            // ISO timestamp
  resolved_at: string | null;
  action_requests: {             // joined from action_requests table
    command: { raw: string; argv: string[] };
    parsed_action: {
      tool: string;              // "terraform", "psql", "shell"
      operation: string;         // "apply", "destroy", "query"
      action_type: string;       // "infrastructure_modify", etc.
      is_destructive: boolean;
    };
    decision: string;            // "REQUIRE_HUMAN_APPROVAL"
    environment: string;         // "production", "staging"
    risk_level: string;          // "HIGH", "CRITICAL"
    risk_score: number;          // 0–20+
    risk_factors: {
      action_weight: number;
      environment_weight: number;
      blast_radius_weight: number;
      reversibility_weight: number;
      privilege_weight: number;
    };
    agent_id: string | null;
    project_id: string;
    original_task: string | null;
  };
}
```

---

## Pages to build (priority order)

### 1. Approvals page `/approvals` ← **build this first**

This is the core demo page. An agent triggers `terraform apply` in production, the CLI hangs showing a spinner, and a human opens this page, sees the request, and clicks Approve.

**What it needs:**
- Live-updating table of **pending** approvals (poll every 5s with SWR or `setInterval`)
- Each row shows: command, environment badge, risk level badge, agent ID, time ago
- Click a row → expand or modal with full details (risk factors breakdown, original task)
- **Approve** button (green) → `POST /api/v1/approvals/{id}/approve` with optional comment
- **Reject** button (red) → `POST /api/v1/approvals/{id}/reject` with required reason
- After approve/reject → remove from pending list immediately (optimistic update)
- Empty state: "No pending approvals 🎉"

**Risk level badge colors:**
- LOW → gray
- MEDIUM → yellow
- HIGH → orange
- CRITICAL → red

**UX note:** The CLI is literally waiting. Latency matters. Approve action should feel instant.

---

### 2. Audit Logs page `/audit` ← second priority

Full history of every command evaluated, regardless of decision.

**What it needs:**
- Sortable, filterable table
- Columns: timestamp, request ID, command, environment, decision, risk level, agent ID, status
- Decision badge colors: ALLOW=green, BLOCK=red, REQUIRE_HUMAN_APPROVAL=yellow
- Filters: environment dropdown, decision dropdown, date range picker
- Click row → `/audit/{request_id}` detail page
- Pagination (20 per page)

> **Note:** There's no `GET /api/v1/actions` list endpoint yet — you'll need to either query Supabase directly from the frontend (using the anon key + Row Level Security) or ask the backend dev to add it. Supabase direct query is fine for now.

---

### 3. Overview / Dashboard page `/` ← third priority

Landing page with counts and recent activity.

**What it needs:**
- 4 stat cards: Total evaluations today / Blocked / Approved / Pending approvals
- "Pending Approvals" card → quick list of last 3 pending with Approve button inline
- "Recent High Risk" table → last 10 CRITICAL/HIGH actions
- All numbers auto-refresh every 30s

**Data source:** Query Supabase directly using the JS client for aggregation queries.

---

### 4. Action Detail page `/audit/{request_id}` ← comes with Audit Logs

Drills into a single action request.

**What it needs:**
- Header: request ID, decision badge, timestamp
- Command section: `code` block with the raw command + argv
- Context section: environment, project, agent ID, working directory, git branch
- Risk breakdown: 5-factor bar chart or table (action/env/blast_radius/reversibility/privilege)
- Policy section: which rule matched, policy ID
- Timeline: all audit events in order (request_created → decision_made → approval_requested → approval_resolved → execution_completed)
- If approved: execution result section (exit code, stdout/stderr preview)

---

### 5. Policies page `/policies` ← lowest priority, read-only

Shows the active policy rules loaded from `policies/default.yaml`.

**What it needs:**
- Table: rule ID, environment, action type, decision, reason
- Color-coded decision column
- Static — no editing in the UI (policies are YAML files, not DB rows)

> **Note:** There's no policies API endpoint yet. Either add one (simple — just returns the loaded policy config from `app.state.policy_config`) or read the YAML file directly and bake it into the page as static data for now.

---

## Component library (shadcn/ui components to install)

```bash
npx shadcn@latest add table badge button dialog card select
npx shadcn@latest add alert tabs separator skeleton tooltip
```

---

## Project structure to follow

```
frontend/
  src/
    app/
      (dashboard)/
        page.tsx              # Overview
        layout.tsx            # Sidebar + header
        approvals/
          page.tsx
        audit/
          page.tsx
          [request_id]/
            page.tsx
        policies/
          page.tsx
    components/
      approvals/
        ApprovalTable.tsx
        ApprovalRow.tsx
        ApprovalModal.tsx
      audit/
        AuditTable.tsx
        RiskFactorsChart.tsx
        AuditTimeline.tsx
      shared/
        DecisionBadge.tsx     # ALLOW/BLOCK/REQUIRE_HUMAN_APPROVAL
        RiskLevelBadge.tsx    # LOW/MEDIUM/HIGH/CRITICAL
        CommandDisplay.tsx    # code block with copy button
    lib/
      api.ts                  # typed fetch wrappers for all backend endpoints
      supabase.ts             # Supabase JS client singleton
      types.ts                # TypeScript types matching the API contract
```

---

## TypeScript types (copy these into `lib/types.ts`)

```typescript
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
}

export interface ActionRequest {
  request_id: string;
  environment: string;
  project_id: string;
  agent_id: string | null;
  original_task: string | null;
  command: { raw: string; argv: string[] };
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
  created_at: string;
  resolved_at: string | null;
  action_requests: ActionRequest;
}
```

---

## API utility functions (copy into `lib/api.ts`)

```typescript
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function listApprovals(status?: string): Promise<Approval[]> {
  const url = status ? `${BASE}/api/v1/approvals?status=${status}` : `${BASE}/api/v1/approvals`;
  const res = await fetch(url);
  const data = await res.json();
  return data.approvals;
}

export async function approveRequest(id: string, comment?: string) {
  return fetch(`${BASE}/api/v1/approvals/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment }),
  });
}

export async function rejectRequest(id: string, reason: string) {
  return fetch(`${BASE}/api/v1/approvals/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
}

export async function getAction(requestId: string): Promise<ActionRequest> {
  const res = await fetch(`${BASE}/api/v1/actions/${requestId}`);
  return res.json();
}
```

---

## Important constraints (don't break these)

| Rule | Reason |
|---|---|
| The frontend can **view** but never **modify** policy rules | Policies are YAML, intentionally not DB rows |
| Approve/reject must show confirmation dialog | Prevents mis-clicks; the CLI is literally waiting |
| Optimistic UI on approve/reject — remove from pending immediately | CLI could be showing to a user; latency is UX |
| No service role key in frontend code | Security — anon key only |
| Approval is for **one specific request** — no bulk approve | Design doc §5: "scoped to a single request" |

---

## Auth (don't implement yet — wait for backend milestone)

Auth is Milestone 3 (backend work). For now, all API endpoints are open. Once auth is added:
- Frontend will use `supabase.auth.signInWithPassword()` or magic link
- Store session in Supabase client (it handles this automatically)
- Pass `Authorization: Bearer {session.access_token}` on all backend API calls
- The `is_approver` flag on the `users` table controls who sees Approve/Reject buttons

---

## How to test your pages

1. Start the backend: `cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload`
2. Trigger a real approval from the CLI (from `examples/terraform/`):
   ```
   agentguard terraform apply
   ```
3. The CLI will hang with a spinner — open your Approvals page and approve it
4. Watch the CLI resolve and execute

This is the demo scenario. Make it look great.
