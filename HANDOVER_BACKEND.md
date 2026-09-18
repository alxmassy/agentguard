# AgentGuard — Backend Handover

> **Source of truth:** Read `agentguard-system-design.md` in the repo root before touching anything. Every architecture decision traces back to it.

---

## What's already built (don't rebuild this)

### Milestone 1 — Core Runtime (complete, 70 tests passing)

| Package | Location | What it does |
|---|---|---|
| FastAPI backend | `backend/` | Evaluates commands, returns ALLOW/BLOCK/REQUIRE_HUMAN_APPROVAL |
| Typer CLI | `cli/` | Intercepts commands, calls backend, executes or blocks |
| Policy Engine | `backend/app/policy/` | Deterministic YAML rules — BLOCK > REQUIRE > ALLOW |
| Risk Engine | `backend/app/risk/` | 5-factor weighted score → LOW/MEDIUM/HIGH/CRITICAL |
| Decision Engine | `backend/app/decision/` | Pure function combining policy + risk + optional intent |
| Server-side re-validator | `backend/app/parser/validator.py` | Never trusts CLI classification |

### Milestone 2 — Database + Approval Workflow (complete)

| What | Location |
|---|---|
| Supabase/PostgreSQL (7 tables) | `supabase/migrations/001_initial_schema.sql` |
| DB client + repositories | `backend/app/db/` |
| POST /api/v1/actions/evaluate | Persists every evaluation, creates approval record |
| GET/POST /api/v1/approvals | List + approve + reject |
| GET/POST /api/v1/actions/{id} | Detail + execution result |
| CLI polling loop | `cli/agentguard_cli/commands/terraform.py` + `exec.py` |

---

## Setup (do this first)

```bash
git clone https://github.com/alxmassy/agentguard.git
cd agentguard

# Install uv (fast Python manager)
irm https://astral.sh/uv/install.ps1 | iex   # Windows PowerShell
# or: curl -LsSf https://astral.sh/uv/install.sh | sh  # Mac/Linux

# Create venv + install both packages
uv venv .venv --python 3.12
uv pip install -e "./backend[dev]" -e "./cli[dev]" --python .venv/bin/python

# Set up .env (get values from Alex)
cp backend/.env.example backend/.env
# Edit backend/.env with real SUPABASE_URL + SUPABASE_SERVICE_KEY

# Run tests — should be 70/70
.venv/bin/python -m pytest tests/ -v

# Start backend
cd backend && uvicorn app.main:app --port 8000 --reload
```

> **Note:** The Supabase migration is already run. Tables exist. You don't need to re-run it unless starting a fresh Supabase project.

---

## What's left for you to build

### Option A — Auth (Milestone 3) ⬅ recommended starting point

**Why first:** Needed before any public deployment. Everything else works without it locally.

**What it is:** JWT-based authentication using Supabase Auth. Every API endpoint requires a valid bearer token.

#### Files to create
```
backend/app/auth/
    __init__.py
    dependencies.py      # FastAPI Depends() that validates JWT
    supabase_auth.py     # calls supabase.auth.get_user(token)
```

#### Files to modify
- `backend/app/api/evaluate.py` — add `user: User = Depends(get_current_user)`
- `backend/app/api/approvals.py` — same; also check `user.is_approver` on POST endpoints
- `backend/app/api/actions.py` — same
- `backend/app/main.py` — tighten CORS `allow_origins` to frontend domain
- `cli/agentguard_cli/main.py` — add `agentguard login` command
- `cli/agentguard_cli/client.py` — send `Authorization: Bearer <token>` header
- `cli/agentguard_cli/config.py` — store/read token from `~/.agentguard/credentials.yaml`

#### Key design rules (from §22 of design doc)
- Use `supabase.auth.get_user(token)` — never decode JWT manually
- CLI token stored in `~/.agentguard/credentials.yaml` (not the project `.agentguard/config.yaml`)
- `is_approver` column on `users` table already exists — read it from `users` table on login and cache it
- Approver check: `POST /approvals/{id}/approve` and `reject` must 403 if `user.is_approver == false`

#### Test the flow
```bash
# Login
agentguard login          # opens browser or prompts email/password
# → stores token in ~/.agentguard/credentials.yaml

# Without token
agentguard terraform plan  # → 401 Unauthorized

# With token
agentguard terraform apply # → works as before, but now attributed to the user
```

---

### Option B — LLM Intent Layer (Milestone 5) — easier, ~2-3 hours

**What it is:** The backend calls an LLM to check whether the command matches the agent's stated task. If there's a mismatch (e.g., task says "update staging" but command targets production), it escalates ALLOW → REQUIRE_HUMAN_APPROVAL.

**Critical rule from §14:** LLM is **advisory only**. It can only escalate, never de-escalate. BLOCK stays BLOCK regardless of what the LLM says. The Decision Engine already handles this — `intent=None` fallback is already coded.

#### Files to create
```
backend/app/intent/
    __init__.py
    engine.py     # calls LLM, returns IntentResult or None
    prompts.py    # prompt templates
```

#### Files to modify
- `backend/app/api/evaluate.py` — after risk assessment, call `assess_intent(validated_request)`, pass result to `decide()`
- `backend/pyproject.toml` — add `openai>=1.0` or `google-generativeai>=0.8`
- `backend/.env.example` — add `OPENAI_API_KEY` or `GEMINI_API_KEY`

#### IntentResult model (already defined in `backend/app/models.py`)
```python
class IntentResult(BaseModel):
    intent: str
    expected_environment: str | None = None
    observed_environment: str | None = None
    mismatch: bool = False
    confidence: float = 0.0
```

#### Key rule: fail safe
If the LLM call fails (timeout, API error, no key), return `None` — not an exception. The decision engine already handles `intent=None` correctly (proceeds with policy+risk only).

---

### Option C — psql Parser (Milestone 6) — moderate, ~4-5 hours

**What it is:** `agentguard psql -- "DROP TABLE payments"` — a proper SQL parser that classifies by actual SQL verb, not heuristics.

#### Files to create
```
cli/agentguard_cli/parser/sql.py          # SQL parser using sqlglot
cli/agentguard_cli/commands/psql.py       # agentguard psql subcommand
backend/app/parser/sql_validator.py       # server-side SQL re-validation
tests/cli/test_sql_parser.py
```

#### Files to modify
- `cli/agentguard_cli/main.py` — register `psql` subcommand
- `cli/pyproject.toml` — add `sqlglot>=23.0`
- `backend/pyproject.toml` — add `sqlglot>=23.0`

#### SQL classification table
| SQL verb | ActionType | is_destructive |
|---|---|---|
| SELECT, EXPLAIN | `database_read` | false |
| INSERT, UPDATE | `database_write` | false |
| DELETE | `database_write` | true |
| DROP TABLE/DATABASE, TRUNCATE | `database_destructive` | true |

---

## Architecture rules you must not break

| Rule | Where enforced |
|---|---|
| BLOCK is absolute — LLM cannot override it | `backend/app/decision/engine.py` — keep this logic |
| Backend re-validates every request | `backend/app/parser/validator.py` — never remove this |
| Never `shell=True` in subprocess | `cli/agentguard_cli/executor.py` |
| Fail safe — backend down = CLI blocks | `cli/agentguard_cli/client.py` returns `None` on error |
| LLM failure = fall back to policy+risk | `intent=None` path in decision engine |
| Policy precedence: BLOCK > REQUIRE > ALLOW > default | `backend/app/policy/engine.py` |

---

## API contract (CLI ↔ Backend)

The CLI and backend define **matching Pydantic models independently** (no shared package). If you add fields, add them to **both** `backend/app/models.py` **and** `cli/agentguard_cli/models.py`.

**Request:** `POST /api/v1/actions/evaluate`
```json
{
  "command": {"raw": "terraform apply", "argv": ["terraform", "apply"]},
  "parsed_action": {"tool": "terraform", "operation": "apply", "action_type": "infrastructure_modify", "is_destructive": false, "is_read_only": false, "raw_args": [], "flags": {}},
  "context": {"agent_id": "claude-code", "project_id": "my-project", "environment": "production"}
}
```

**Response:** `DecisionResponse`
```json
{
  "request_id": "AG-46868425",
  "decision": "REQUIRE_HUMAN_APPROVAL",
  "reason": "Production infrastructure modification requires approval",
  "policy_id": "prod-apply-approval",
  "risk_level": "HIGH",
  "risk_score": 11,
  "risk_factors": {"action_weight": 3, "environment_weight": 4, "blast_radius_weight": 3, "reversibility_weight": 1, "privilege_weight": 0},
  "approval_id": "7c6712fa-0652-432a-9752-599ceece1ef5"
}
```

---

## Running tests

```bash
# All tests
.venv/bin/python -m pytest tests/ -v

# Just backend unit tests
.venv/bin/python -m pytest tests/backend/ -v

# Just integration tests (needs backend importable, no real DB needed)
.venv/bin/python -m pytest tests/integration/ -v
```

**Expected: 70 passed.** If any fail after your changes, investigate before pushing.

---

## Key files to read first

1. `agentguard-system-design.md` — the entire design doc, §1–§30
2. `backend/app/models.py` — all Pydantic models
3. `backend/app/api/evaluate.py` — the evaluation pipeline
4. `backend/app/decision/engine.py` — decision logic (most critical)
5. `policies/default.yaml` — the 13 policy rules
