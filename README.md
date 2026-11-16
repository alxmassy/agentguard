# AgentGuard — AI Agent Runtime Safety & Governance Layer

AgentGuard is a runtime safety and governance platform that sits between autonomous AI coding/infrastructure agents (Claude Code, Cursor, Codex) and consequential actions they attempt to execute.

```
AI Agent → agentguard CLI Gateway → Backend Evaluation →
  Deterministic Policy + 5-Factor Risk Engine →
  Decision (ALLOW / BLOCK / REQUIRE_HUMAN_APPROVAL) →
  Execute or Halt → Live Audit Trail → Web Dashboard
```

---

## 🎯 Key Objectives

1. **Pre-execution Control:** Dangerous actions are stopped *before* the subprocess runs, not just logged after the damage is done.
2. **Deterministic Authority:** Safety decisions are enforced by explicit deterministic policies. LLMs are advisory only and cannot override a policy `BLOCK`.
3. **Fail-Closed Architecture:** Network or database outages default to `BLOCK` or `REQUIRE_HUMAN_APPROVAL`, never `ALLOW`.
4. **Human-in-the-Loop:** High-impact modifications pause the CLI until an authorized human approves them via the web dashboard.
5. **Auditability:** Complete, queryable lifecycle event log for compliance and post-incident review.

---

## 🏛️ System Architecture

- **CLI Gateway (`agentguard`):** Typer-based developer and agent gateway with strict subprocess security (`shell=False`, environment allowlisting, execution timeout).
- **Backend API (FastAPI):** High-performance safety engine with server-side re-validation, deterministic rule precedence, and dual storage (Supabase PostgreSQL + local SQLite).
- **Web Dashboard (Next.js 15 + Tailwind CSS):** Modern control plane with real-time approval polling, risk factor visualization, and filterable audit trails.

---

## ⚡ Quick Start for College Presentation

### 1. Start the Backend API

```powershell
# From the project root
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000 --reload
```
API runs at `http://localhost:8000`. OpenAPI docs available at `http://localhost:8000/docs`.

### 2. Start the Frontend Dashboard

```powershell
cd frontend
$env:PATH = "C:\Program Files\nodejs;$env:PATH"
npm.cmd run dev
```
Dashboard runs at `http://localhost:3000`.

---

## 🎬 Presentation Demo Walkthrough (5-Minute Script)

### Step 1: Open the Dashboard
Open `http://localhost:3000` in your browser. Show the overview stat cards, system status, and active governance rules.

### Step 2: Safe Action (`ALLOW`)
Run a read-only command in the terminal:
```powershell
cd examples\terraform
..\..\.venv\Scripts\agentguard.exe terraform plan
```
- **Outcome:** Green `ALLOWED` banner printed in terminal.
- **Result:** Command executes safely; audit event appears live in the dashboard.

### Step 3: Destructive Action Veto (`BLOCK`)
Attempt to destroy production infrastructure:
```powershell
..\..\.venv\Scripts\agentguard.exe terraform destroy
```
- **Outcome:** Red `BLOCKED` banner with `prod-destroy-block` and CRITICAL risk score 20.
- **Result:** Command **never reaches the system**. Dashboard records the blocked threat.

### Step 4: Human-in-the-Loop (`REQUIRE_HUMAN_APPROVAL`)
Attempt a high-impact production modification:
```powershell
..\..\.venv\Scripts\agentguard.exe terraform apply
```
- **Outcome:** CLI displays a live spinner: `Waiting for approval [AG-xxxx]...`
- **Dashboard Action:** Switch to the browser at `http://localhost:3000/approvals`.
- **Result:** See the pending card with 5-factor risk weight breakdown. Click **Approve**.
- **CLI Resolution:** The terminal instantly updates with `✓ Approved!` and completes execution!

---

## 📊 5-Factor Risk Weight Scoring

$$\text{Risk Score} = \text{Action} + \text{Environment} + \text{Blast Radius} + \text{Reversibility} + \text{Privilege}$$

| Score Range | Risk Level |
|---|---|
| 0 – 3 | `LOW` |
| 4 – 7 | `MEDIUM` |
| 8 – 12 | `HIGH` |
| 13+ | `CRITICAL` |

---

## 🧪 Testing & Verification

Run the comprehensive test suite (75 tests):
```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```
All unit tests and integration tests pass with 100% green status.
