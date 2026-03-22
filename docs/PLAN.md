# PLAN.md — Project Roadmap & Progress Tracker
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: LIVE — update every session
# ============================================================
# AI reads this file at the START of every session (after STATE.md).
# AI updates the Current Status block and stage checkboxes at END of every session.
# Never mark a step ✅ without running the acceptance criteria.
# ============================================================

## 📍 Current Status
*(AI updates this block every session — read first, update last)*

**Stage:** Stage 1 — Project Setup
**Step:** 1.3 — CI Skeleton
**Status:** 🔄 In Progress
**Updated:** 2026-03-22
**Blockers:** None
**Next action:** Pre-flight and draft CI configuration (ci.yml)

> ⚠️ STATE.md is the authoritative source for current position.
> If STATE.md and this block disagree — STATE.md wins. Update this block to match.

---

## Stage Overview

| Stage | Name | Status | Description |
|-------|------|--------|-------------|
| **0** | **Proof of Concept** | ✅ Done | **Single script proving the core works end-to-end. Do this first.** |
| 1 | Project Setup | 🔄 In Progress | Repo, environment, CI skeleton, Z3 smoke test |
| 2 | Core Infrastructure | ⬜ Not Started | DB schema, Neo4j graph model, FastAPI skeleton, React scaffold, auth |
| 3 | Pipeline Features | ⬜ Not Started | All 7 PRD features — ingestion → CI → CT → CD → certificates → HCI |
| 4 | Security Hardening | ⬜ Not Started | Auth enforcement, HMAC, rate limiting, PII audit, env audit |
| 5 | Testing | ⬜ Not Started | Unit coverage, integration tests, E2E flows, CI gates |
| 6 | Polish & Deploy | ⬜ Not Started | Performance, accessibility, README, Railway deploy |

**Status icons:** ⬜ Not Started · 🔄 In Progress · ✅ Done · 🚫 Blocked

---

## Stage 0: Proof of Concept
*Goal: One script. One real RBI rule. One loan model. Z3 proves compliance or violation. Runs in under 60 seconds. No database. No API. No frontend. Just the core.*

**Why Stage 0 exists:**
The entire system is built around one claim: "Z3 can verify that an ML model complies with RBI regulations." Stage 0 proves that claim is real before writing a single line of infrastructure. This is the demo that silences "cool architecture, where does it run?" It should be completable in one afternoon session.

**Output:** `scripts/poc_pipeline.py` — a single runnable file that demonstrates the full innovation loop.

### 0.1 Minimal Z3 Compliance Check

- [x] Install only what's needed: `pip install z3-solver openai python-dotenv`
- [x] Create `scripts/poc_pipeline.py` — single file, no imports from `src/`
- [x] Hardcode one real RBI rule as a Z3 formula directly in the script:
  ```python
  # RBI Master Direction §4.1 — Digital Lending 2022
  # "Loan service providers shall not use discriminatory variables
  #  including but not limited to: caste, religion, gender, or
  #  geographic proxies such as PIN codes in credit decision models"
  
  from z3 import *
  
  # Model feature weights (what the loan model actually uses)
  income_weight      = Real('income_weight')
  credit_score_weight = Real('credit_score_weight')
  pin_code_weight    = Real('pin_code_weight')   # THIS is the violation
  
  # RBI Rule §4.1 encoded as Z3 constraint:
  # "pin_code_weight must be zero — geographic proxies are prohibited"
  rbi_rule = (pin_code_weight == 0)
  
  # Test Model A — COMPLIANT (no pin code)
  model_a = And(income_weight > 0, credit_score_weight > 0, pin_code_weight == 0)
  
  # Test Model B — VIOLATION (uses pin code)
  model_b = And(income_weight > 0, credit_score_weight > 0, pin_code_weight > 0)
  ```
- [x] Run Z3 check on both models — print COMPLIANT / VIOLATION + counterexample
- [x] Verify: Model A → UNSAT (no violation found), Model B → SAT + counterexample showing `pin_code_weight = 0.3`

**Acceptance criteria:** `python scripts/poc_pipeline.py` outputs:
```
Model A: COMPLIANT ✓ — satisfies RBI §4.1 (no geographic proxy used)
Model B: VIOLATION ✗ — RBI §4.1 violated
  Counterexample: pin_code_weight = 0.3 (prohibited geographic proxy)
  Plain English: This model assigns weight 0.3 to PIN code,
                 which is a geographic proxy prohibited under
                 RBI Master Direction §4.1 (Digital Lending 2022)
```

### 0.2 LLM Rule Extraction (Live)

- [x] Add OpenRouter call to `poc_pipeline.py`:
  ```python
  import openai, os
  from dotenv import load_dotenv
  load_dotenv()
  
  client = openai.OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=os.environ["OPENROUTER_API_KEY"]
  )
  
  RAW_RBI_TEXT = """
  RBI Master Direction – Digital Lending, 2022, Section 4.1:
  Regulated Entities shall ensure that the algorithm used for
  credit underwriting does not use discriminatory data points
  including caste, religion, gender, or geographic proxies
  such as PIN codes or locality names.
  """
  
  response = client.chat.completions.create(
      model="anthropic/claude-3-5-sonnet",
      messages=[{
          "role": "user",
          "content": f"""Extract this regulation as a Z3 Python constraint.
  Return ONLY valid Python code using z3 library. No explanation.
  Format: variable_name = Real('variable_name'); rule = (constraint)
  
  Regulation: {RAW_RBI_TEXT}"""
      }]
  )
  candidate_formula = response.choices[0].message.content
  print(f"LLM candidate formula:\n{candidate_formula}")
  ```
- [x] Print candidate formula — show it's a real Z3 expression
- [x] Run Z3 `parse_smt2_string` to validate formula is well-formed before using it
- [x] If malformed: print `REJECTED — formula is not valid Z3 syntax: {error}`
- [x] If well-formed: print `VALIDATED — formula is structurally sound, ready for human review`

**Acceptance criteria:** Script calls OpenRouter, gets a Z3 formula back, Z3 validates it's parseable, prints VALIDATED or REJECTED with reason.

### 0.3 Confidence Score (Live Calculation)

- [x] Add confidence scoring to `poc_pipeline.py` — three signals, one score:
  ```python
  def calculate_confidence(
      raw_text: str,
      candidate_formula: str,
      z3_parse_result: bool
  ) -> dict:
      """
      Confidence score = weighted average of 3 signals.
      Tells the compliance officer how much to trust the LLM extraction.
      """
      signals = {}
  
      # Signal 1 — Formula completeness (0.0–1.0)
      # Does the formula contain the key legal terms from the source text?
      key_terms = extract_key_legal_terms(raw_text)  # nouns + prohibitions
      terms_captured = sum(
          1 for term in key_terms
          if term.lower() in candidate_formula.lower()
      )
      signals["completeness"] = terms_captured / max(len(key_terms), 1)
  
      # Signal 2 — Z3 structural validity (0.0 or 1.0 — binary)
      # Did Z3 accept the formula without parse errors?
      signals["z3_valid"] = 1.0 if z3_parse_result else 0.0
  
      # Signal 3 — Formula specificity (0.0–1.0)
      # Is the formula specific (has real variable names) or generic (uses x1, x2)?
      z3_vars = re.findall(r"Real\('(\w+)'\)", candidate_formula)
      meaningful_vars = [v for v in z3_vars if len(v) > 2 and not v.startswith('x')]
      signals["specificity"] = min(len(meaningful_vars) / 3, 1.0)
  
      # Weighted final score
      score = (
          signals["completeness"] * 0.5 +
          signals["z3_valid"]     * 0.3 +
          signals["specificity"]  * 0.2
      )
  
      return {
          "score": round(score, 2),
          "signals": signals,
          "recommendation": (
              "HIGH CONFIDENCE — safe to review and approve"   if score >= 0.75 else
              "MEDIUM CONFIDENCE — review carefully"           if score >= 0.50 else
              "LOW CONFIDENCE — recommend manual re-extraction"
          )
      }
  ```
- [x] Print confidence result alongside the candidate formula
- [x] Low confidence (<0.50) → script prints warning, suggests manual re-extraction

**Acceptance criteria:** Script prints a confidence score between 0.0–1.0 with the three signal breakdown and a plain-English recommendation. Score is deterministic for the same input.

### 0.4 Full PoC Run — End to End

- [x] Chain all three steps in `poc_pipeline.py`:
  ```
  1. Read raw RBI regulation text (hardcoded string)
  2. Call OpenRouter → get candidate Z3 formula
  3. Calculate confidence score (3 signals)
  4. Z3 validates formula well-formedness
  5. Print: formula + confidence + VALIDATED/REJECTED
  6. If VALIDATED + confidence >= 0.50:
       Run Z3 check against Model A (compliant) → print COMPLIANT
       Run Z3 check against Model B (violation) → print VIOLATION + counterexample
  7. Print plain-English explanation of the counterexample
  8. Print proof hash: sha256(formula + model_constraints + result)
  ```
- [x] Run the complete script: `python scripts/poc_pipeline.py`
- [x] Total runtime must be under 60 seconds (LLM call + Z3 checks)

**The PoC acceptance criteria — this is the demo:**
```
=== REGO PROOF OF CONCEPT ===
Regulation: RBI Master Direction §4.1 — Digital Lending 2022

Step 1: LLM Extraction
  Candidate formula: pin_code_weight == 0
  Confidence: 0.82 (HIGH — safe to review)
    completeness: 0.85 | z3_valid: 1.0 | specificity: 0.75

Step 2: Z3 Validation
  Formula well-formedness: VALIDATED ✓

Step 3: Compliance Check
  Model A (no pin code):  COMPLIANT ✓
  Model B (uses pin code): VIOLATION ✗
    Counterexample: pin_code_weight = 0.30
    Plain English: Model uses PIN code as a feature (weight: 0.30).
                   RBI §4.1 prohibits geographic proxies in credit decisions.

Step 4: Proof
  Proof hash: sha256:a1b2c3d4e5f6...
  Timestamp: 2026-03-20T18:00:00Z

=== DONE in 8.3 seconds ===
```

**Once Stage 0 is complete:** You have a running system. Every subsequent stage is infrastructure around this core.

---

---

## Stage 1: Project Setup
*Goal: A running skeleton where Z3 proves a formula, FastAPI returns `/health`, and React loads. Nothing more.*

### 1.1 Repository & Dependency Setup
- [ ] `git init rego-mlops` — initialize repository
- [ ] Create folder structure exactly as specified in ARCHITECTURE.md Section 1 (`src/`, `frontend/`, `.github/workflows/`, `docs/`, `system/`, `scripts/`, `tests/`)
- [ ] Create `pyproject.toml` with all pinned versions from TECH.md Section 5
- [ ] Run `poetry install` — verify clean install with no resolution errors
- [ ] Create `frontend/package.json` with all pinned versions from TECH.md Section 5
- [ ] Run `npm install` inside `frontend/` — verify clean install
- [ ] Create `.env.example` with all 18 variables from ARCHITECTURE.md Section 6
- [ ] Create `.env` from `.env.example` — fill in real values (never commit)
- [ ] Verify `.gitignore` includes: `.env`, `mlruns/`, `__pycache__/`, `node_modules/`, `.venv/`
- [ ] Run `python scripts/verify_z3_install.py` — must print Z3 version and `Z3 OK`
- [ ] **Kaggle setup (one time):** Create account at kaggle.com → Account → API → Create New Token → downloads `kaggle.json` → add `KAGGLE_USERNAME` and `KAGGLE_KEY` to `.env` and GitHub Actions secrets → run `pip install kaggle` → run `kaggle datasets list` to confirm auth works

**Acceptance criteria:** `poetry run python -c "import z3; print(z3.get_version_string())"` prints a version. `npm run dev` starts Vite without errors.

### 1.2 Linting & Type Checking
- [ ] Configure `ruff` in `pyproject.toml` — enable import-order rules that enforce three-layer separation (AIRULES Rule 8)
- [ ] Configure `mypy` in `pyproject.toml` — strict mode, `disallow_untyped_defs = true`
- [ ] Configure `black` for formatting
- [ ] Create `frontend/tsconfig.json` with `strict: true` and path aliases from ARCHITECTURE.md Section 5
- [ ] Configure `vite.config.ts` with path alias resolution matching `tsconfig.json`
- [ ] Configure `eslint` with TypeScript rules — `no-explicit-any` enabled
- [ ] Run `ruff check src/` — zero errors on empty scaffold
- [ ] Run `mypy src/` — zero errors on empty scaffold
- [ ] Run `npm run lint` in `frontend/` — zero errors

**Acceptance criteria:** All three linters pass on the empty scaffold. `ruff`, `mypy`, `eslint` exit 0.

### 1.3 CI Skeleton
- [ ] Create `.github/workflows/ci.yml` — runs on every PR: ruff + mypy + pytest (no tests yet, just collects) + eslint + vitest
- [ ] Create `.github/workflows/cd.yml` — stub only, no deploy steps yet
- [ ] Create `.github/workflows/ct.yml` — stub only, workflow_dispatch trigger wired up
- [ ] Push to GitHub — verify CI workflow appears in Actions tab and passes (0 tests = pass)
- [ ] Add GitHub Actions secrets: `OPENROUTER_API_KEY`, `SUPABASE_TEST_URL`, `NEO4J_TEST_URI`

**Acceptance criteria:** A push to `main` triggers the CI workflow. It passes. GitHub Actions tab shows a green run.

### 1.4 Docker Local Dev
- [ ] Write `Dockerfile` — multi-stage: builder (poetry install) → runtime (copy built artifacts)
- [ ] Write `docker-compose.yml` — services: `api` (FastAPI), `neo4j` (community edition, local), `supabase` (via Supabase CLI local dev)
- [ ] Run `docker compose up` — all three services start without errors
- [ ] Verify FastAPI is reachable at `http://localhost:8000/health`
- [ ] Verify Neo4j browser at `http://localhost:7474`

**Acceptance criteria:** `docker compose up` brings up all services. `curl localhost:8000/health` returns `{"status": "ok"}`.

---

## Stage 2: Core Infrastructure
*Goal: Auth works, DB schema exists, Neo4j graph model seeded, FastAPI routing skeleton in place, React scaffold renders with role-based routing.*

### 2.1 Supabase — Database Schema
- [ ] Create Supabase project (free tier) — save URL and keys to `.env`
- [ ] Write migration: `users` table (id, email, role: `compliance_officer | ml_engineer | cto`, created_at)
- [ ] Write migration: `regulations` table (id, rule_id, jurisdiction, source_text, formal_logic, status: `extracted | z3_validated | z3_rejected | pending_approval | approved | rejected | active`, version, created_at, approved_by, approved_at)
- [ ] Write migration: `certificates` table (id, model_version, regulation_versions JSONB, proof_hash, hmac_signature, created_at) — NO updated_at (immutable — AIRULES Rule 4)
- [ ] Write migration: `pipeline_events` table (id, stage, gate_name, status, model_version, rule_ids JSONB, duration_ms, plain_english_result, created_at)
- [ ] Run migrations against local Supabase — verify schema in Supabase Studio
- [ ] Seed test users: one per role (`co@test.rego.dev`, `mle@test.rego.dev`, `cto@test.rego.dev`)

**Acceptance criteria:** Supabase Studio shows all 4 tables. Test users exist. `certificates` table has no `updated_at` column (immutability enforced at schema level).

### 2.2 Neo4j — Knowledge Graph Model
- [ ] Connect to Neo4j Aura free instance — save URI to `.env`
- [ ] Design and document node types: `(:Regulation {rule_id, version, jurisdiction, status})`, `(:ModelVersion {version, artifact_path, created_at})`, `(:ProofCertificate {cert_id, proof_hash})`
- [ ] Design and document relationship types: `(:ModelVersion)-[:COMPLIANT_WITH]->(:Regulation)`, `(:ProofCertificate)-[:CERTIFIES]->(:ModelVersion)`, `(:Regulation)-[:SUPERSEDES]->(:Regulation)`
- [ ] Write `scripts/seed_rbi_rules.py` — seeds 3 sample RBI Master Direction rules as `(:Regulation)` nodes with status `active`
- [ ] Run seed script — verify nodes appear in Neo4j Browser
- [ ] Write `lib/neo4j_client.py` — connection pool (max_size=1 for free tier), `run()`, `close()`, typed return

**Acceptance criteria:** `python scripts/seed_rbi_rules.py` exits 0. Neo4j Browser shows 3 `Regulation` nodes with `rule_id` values starting with `RBI-MD-2022-`.

### 2.3 FastAPI Skeleton
- [ ] Create `src/api/main.py` — FastAPI app, CORS middleware (localhost:5173 in dev), request ID middleware
- [ ] Create `src/api/dependencies.py` — `get_current_user()` dependency: validates Supabase JWT, returns user with role
- [ ] Create `src/api/routes/health.py` — `GET /health` (no auth), `GET /health/z3` (Z3 smoke test, no auth)
- [ ] Create all route files as stubs: `regulations.py`, `pipeline.py`, `certificates.py`, `models.py` — each returns `{"status": "not_implemented"}` for now
- [ ] Register all routers in `main.py`
- [ ] Write `src/api/schemas/` — all 4 schema files from ARCHITECTURE.md with placeholder models
- [ ] Test: `GET /health` → 200, `GET /health/z3` → 200 with Z3 version

**Acceptance criteria:** `poetry run uvicorn src.api.main:app --reload` starts. All routes return responses (even stubs). `/docs` shows Swagger UI with all routes listed.

### 2.4 Supabase Auth + Role-Based Routing
- [ ] Configure Supabase Auth — email+password only (no OAuth for MVP)
- [ ] Add `role` to Supabase user metadata on signup
- [ ] Implement `get_current_user()` in `dependencies.py` — decodes JWT, fetches role from `users` table
- [ ] Implement role-enforcement helper: `require_role(allowed_roles: list[str])` — returns 403 if role not in list
- [ ] Create `frontend/src/lib/auth/supabase.ts` — Supabase client init
- [ ] Create `frontend/src/lib/auth/useAuth.ts` — returns `{user, role, isLoading, signIn, signOut}`
- [ ] Create `frontend/src/router/index.tsx` — role-based routing: `compliance_officer` → `/compliance-officer/*`, `ml_engineer` → `/ml-engineer/*`
- [ ] Create `frontend/src/components/layout/RootLayout.tsx` — checks auth, redirects to login if unauthenticated
- [ ] Test: Login as CO → redirected to CO dashboard. Login as MLE → redirected to MLE dashboard. Unauthenticated → login page.

**Acceptance criteria:** Three test users each land on the correct interface after login. `POST /api/regulations/{id}/approve` with MLE JWT returns 403.

### 2.5 React Scaffold — Both Interfaces
- [ ] Create `frontend/src/features/compliance-officer/` folder structure from ARCHITECTURE.md
- [ ] Create `frontend/src/features/ml-engineer/` folder structure from ARCHITECTURE.md
- [ ] Create `frontend/src/components/ui/` — Button, Badge, Card, StatusDot, LoadingSpinner (from DESIGN.md specs)
- [ ] Create `frontend/src/components/layout/COLayout.tsx` and `MLELayout.tsx` — shells with nav
- [ ] Create stub pages for CO: Dashboard, RegulationUpload, ApprovalQueue, Certificates
- [ ] Create stub pages for MLE: PipelineMonitor, ViolationReport, ModelDiff, ModelRegistry
- [ ] Wire all stubs to router — each renders its name as an `<h1>` for now
- [ ] Verify: CO login → sees "Dashboard" heading. MLE login → sees "Pipeline Monitor" heading.

**Acceptance criteria:** All 8 pages render without errors. Navigation between pages works. No cross-role access.

---

## Stage 3: Pipeline Features
*Goal: All 7 PRD features working end-to-end. This is the core of Rego.*

### 3.1 Feature 1 — Regulatory Ingestion Engine
*"CO pastes law → LLM extracts logic → CO approves → rule enters knowledge graph"*

**Dependencies:** Stage 2 complete (Neo4j, Supabase schema, auth)

- [ ] Create `src/lib/llm_client.py` — OpenRouter client, `extract_rules(text: str) -> list[RuleLogic]`, fallback model on 429, 3-retry exponential backoff
- [ ] Create `src/pipeline/ingestion/extractor.py` — calls LLM client, parses response into `RuleLogic` Pydantic models, handles malformed output
- [ ] Create `src/pipeline/ingestion/validator.py` — Z3 parse + well-formedness check: `validate(formula: str) -> ValidationResult` returning `z3_validated | z3_rejected` with rejection reason. Malformed formulas never reach the approval queue.
- [ ] Create `src/pipeline/ingestion/versioner.py` — writes approved rule to Neo4j as `(:Regulation)` node with version ID `RBI-{section}-{timestamp}`
- [ ] Create `src/pipeline/ingestion/approver.py` — 5-state machine: `extracted → z3_validated → pending_approval → approved | rejected` (also `extracted → z3_rejected` short-circuit). Z3-rejected rules surface parse failure to CO. Invalid transitions raise `InvalidStateTransitionError`
- [ ] Implement `POST /api/regulations` route — accepts text, triggers async extraction, returns job ID
- [ ] Implement `GET /api/regulations` route — returns list of active + pending rules
- [ ] Implement `POST /api/regulations/{id}/approve` — CO role only, triggers state transition
- [ ] Implement `POST /api/regulations/{id}/reject` — CO role only
- [ ] Build CO RegulationUpload page — drag-drop dropzone (`react-dropzone`), extraction loading state, rule translation card with approve/reject (two-click flow per AIRULES Rule 39)
- [ ] Build CO ApprovalQueue page — list of pending rules, each with approve/reject controls

**Acceptance criteria:**
- CO pastes text → rule appears in approval queue within 30s (LLM latency)
- CO rejects → rule status = `rejected`, does not appear in active rules
- CO approves (two clicks) → rule status = `active`, appears in Neo4j as `(:Regulation)` node
- MLE cannot access approve endpoint (403)
- LLM timeout → inline error shown in CO interface, no crash

### 3.2 Feature 2 — Regulatory Version Control & Lineage Graph
*"Law versions + model versions tracked together — answer: which law was this model compliant with?"*

**Dependencies:** Feature 3.1 (regulations in Neo4j), Stage 2 (Neo4j client)

- [ ] Extend `versioner.py` — each new regulation version creates `(:Regulation)-[:SUPERSEDES]->(:Regulation)` edge to previous version
- [ ] Create `src/pipeline/cd/lineage.py` — writes `(:ModelVersion)-[:COMPLIANT_WITH]->(:Regulation)` edges for each regulation version active at deploy time
- [ ] Implement `GET /api/models/{version}/lineage` route — returns model version's full compliance lineage (which regulation versions, when active)
- [ ] Build MLE ModelRegistry page — table of model versions, each row shows linked regulation versions
- [ ] Build CO Certificates page — each certificate shows: model version, regulation version(s), proof hash

**Acceptance criteria:**
- `GET /api/models/v2.1.4/lineage` returns JSON with at least one `regulation_version` entry
- When a regulation is superseded, old `(:Regulation)` node remains with `status: superseded` — lineage history preserved
- CO can see which version of which RBI direction any deployed model was certified against

### 3.3 Feature 3 — Compliance-Aware CI Gates
*"Model submission → symbolic checks → all gates pass or pipeline halts with exact violation"*

**Dependencies:** Feature 3.1 (active rules in Neo4j), Z3 client

- [ ] Create `src/lib/z3_client.py` — `prove(formula, constraints) -> ProofResult`, `counterexample(formula, constraints) -> Counterexample`, structured logging on every call (AIRULES Rule 15)
- [ ] Create `src/pipeline/ci/symbolic_check.py` — fetches all active rules from Neo4j, runs Z3 against each, returns `GateResult`
- [ ] Create `src/pipeline/ci/reg_attack.py` — adversarial edge-case tests: constructs boundary scenarios for each active rule, verifies model handles them correctly
- [ ] Create `src/pipeline/ci/fairness_check.py` — Evidently AI fairness metrics: demographic parity check, returns pass/fail with metric values
- [ ] Create `src/pipeline/ci/regression.py` — performance regression test: new model vs baseline on held-out test set, fails if F1 drops >5%
- [ ] Create `src/pipeline/ci/reporter.py` — translates Z3 counterexample into plain English (LLM-assisted, offline), never sends raw Z3 to CO interface (AIRULES Rule 38)
- [ ] Create `src/pipeline/ci/gate_runner.py` — runs all gates in order: symbolic → reg_attack → fairness → regression. First failure halts, calls reporter
- [ ] Implement `POST /api/pipeline/submit` route — accepts model artifact path, triggers CI gate sequence
- [ ] Implement `GET /api/pipeline/status` route — returns current gate status per gate
- [ ] Implement WebSocket `WS /api/pipeline/events` — streams real-time gate events
- [ ] Build MLE PipelineMonitor page — live gate rows (PASS/FAIL/RUNNING/QUEUED), WebSocket-connected
- [ ] Build MLE ViolationReport page — rule ID in monospace, plain English explanation, Z3 counterexample (for MLE only, not CO)

**Acceptance criteria:**
- Submit compliant model → all 4 gates pass → `GateResult.status = COMPLIANT` for each
- Submit model using postal_code feature → symbolic check fails → violation report shows `RBI-MD-2022-§4.1` and plain English explanation
- MLE sees Z3 counterexample variables. CO never sees them.
- Gate failure halts pipeline — `regression.py` never runs if `symbolic_check.py` fails
- Real-time WebSocket: gate status updates in MLE interface within 1s of gate completion

### 3.4 Feature 4 — Regulatory-Triggered CT
*"New regulation detected → automatic retraining — law drift, not data drift"*

**Dependencies:** Feature 3.1 (regulations in Neo4j), GitHub Actions CT workflow

- [ ] Create `src/pipeline/ct/drift_detector.py` — polls Neo4j for new/amended `(:Regulation)` nodes since last check timestamp, returns `RegulationDrift` object if change detected
- [ ] Create `src/pipeline/ct/trigger.py` — calls GitHub Actions workflow dispatch API when drift detected, passes `regulation_version` as input
- [ ] Create `src/pipeline/ct/constraint_loss.py` — custom PyTorch loss term: penalizes model for using features prohibited by active regulation rules
- [ ] Create `notebooks/ct_retrain.ipynb` — Kaggle notebook that: loads training data, retrains XGBoost with `constraint_loss` penalty for prohibited features, saves `model.pkl` to `/kaggle/working/`
- [ ] Create `src/pipeline/ct/trigger.py` — Kaggle API client: `push_notebook()` to trigger run, `poll_until_complete()` to wait, `pull_output()` to download `model.pkl`
- [ ] Create `src/pipeline/ct/trainer.py` — local wrapper that calls trigger.py, registers pulled model in MLflow with `regulation_version` tag
- [ ] Update `.github/workflows/ct.yml` — workflow dispatch: runs drift_detector → if drift → trigger trainer → log to MLflow → submit to CI
- [ ] Implement `POST /api/pipeline/trigger-ct` route — manual CT trigger (MLE role), for testing without waiting for regulation change

**Acceptance criteria:**
- Add a new regulation rule → within 5 minutes, CT workflow appears in GitHub Actions
- CT run creates new MLflow experiment run tagged with `regulation_version`
- `constraint_loss` causes training to penalize the prohibited feature — verify by checking feature importance of retrained model
- Manual trigger via `POST /api/pipeline/trigger-ct` works for testing

### 3.5 Feature 5 — Compliance-Gated CD
*"Model passes all CI gates → proof certificate generated → zero-downtime deploy → < 3 minutes law to production"*

**Dependencies:** Feature 3.3 (CI gates), Feature 3.2 (lineage), Supabase certificates table

- [ ] Create `src/pipeline/cd/certificate.py` — generates `ProofCertificate`: collects Z3 proof hashes from CI run, gathers active regulation versions, computes HMAC signature using `PROOF_CERT_SECRET`, writes to Supabase (write-once, AIRULES Rule 4)
- [ ] Add HMAC re-verification to `GET /api/certificates/{id}` — detects tampered certificates (AIRULES Rule 33)
- [ ] Create `src/pipeline/cd/canary.py` — deploys to 10% traffic on Railway, runs shadow compliance check, promotes to 100% if no violations
- [ ] Create `src/pipeline/cd/deployer.py` — Railway deploy via API, zero-downtime swap, rolls back if deploy fails
- [ ] Implement `POST /api/pipeline/deploy` route — MLE role, triggers CD after CI pass confirmation
- [ ] Implement `GET /api/certificates/{id}` route — returns certificate with HMAC verification
- [ ] Implement `GET /api/certificates` route — returns list of all certificates (latest first)
- [ ] Build CO Certificates page — table of certificates, download button per row, proof hash displayed

**Acceptance criteria:**
- Compliant model → certificate created in Supabase → `GET /api/certificates/{id}` returns 200 with valid HMAC
- Second deploy attempt of same model version → 409 Conflict (immutability enforced)
- Tampered certificate (modified proof_hash) → `GET /api/certificates/{id}` returns 422
- Certificate shows model version AND regulation version(s) — not model version alone
- CO can download certificate as JSON file from dashboard

### 3.6 Feature 6 — Proof Certificate Generation (display + verification)
*"Auditor verifies compliance in < 10 seconds"*

**Dependencies:** Feature 3.5 (certificates in Supabase)

- [ ] Build CO ProofCertificateView component — indigo card, model version, regulation versions, full Z3 hash, copy hash button, download JSON button (from DESIGN.md)
- [ ] Build MLE certificate row in ModelRegistry — links each model version to its certificate
- [ ] Create `scripts/generate_dev_certificate.py` — generates a local test certificate without running full pipeline (for UI development)
- [ ] Add certificate verification endpoint: `POST /api/certificates/verify` — accepts `{cert_id, proof_hash}`, returns `{valid: true/false}` — no auth required (for auditors)

**Acceptance criteria:**
- CO can reach any certificate from dashboard in ≤ 2 clicks
- CO clicks "Copy Hash" → hash in clipboard
- CO clicks "Download" → JSON file with cert data
- Auditor POSTs `{cert_id, proof_hash}` to `/verify` → gets `{valid: true}` in < 300ms
- Forged hash → `{valid: false}` with tamper explanation

### 3.7 Feature 7 — HCI Dashboard (full implementation)
*"Two complete interfaces — CO sees plain English, MLE sees everything"*

**Dependencies:** All of 3.1–3.6

- [ ] Build CO Dashboard — hero compliance status bar (full-width, color + text, DESIGN.md Section 8), active rules list, pending approvals count, recent certificates table
- [ ] Build MLE Dashboard — pipeline status overview, recent model versions, CI gate history, regulation drift log
- [ ] Implement real-time compliance status — Supabase Realtime subscription on `pipeline_events` table → WebSocket → Zustand store → status badge updates without page refresh
- [ ] Implement plain-English status everywhere in CO interface — no rule IDs, no Z3 terms, no technical jargon
- [ ] Build visual model diff — MLE ModelDiff page: shows features added/removed between two model versions, highlights compliance-impacting changes in red
- [ ] Verify all 5 HCI principles from PRD.md Section 7 are implemented structurally (not just in UI copy)

**Acceptance criteria:**
- New violation detected → CO compliance badge changes from green to red within 3 seconds (no page refresh)
- CO dashboard has zero technical jargon — compliance officer with no ML knowledge can understand every element
- MLE sees exact Z3 counterexample for any violation
- Both dashboards work on 1280px+ screen width without horizontal scroll
- All loading states show descriptive text (AIRULES Rule 40)

---

## Stage 4: Security Hardening
*Goal: Every security rule from AIRULES.md verified. No auth gaps, no data leaks, no PII in logs.*

### 4.1 Authentication & Authorization Audit
- [ ] Audit every FastAPI route — confirm `Depends(get_current_user)` on every non-health route
- [ ] Audit role enforcement — confirm `require_role()` applied to CO-only and MLE-only endpoints
- [ ] Test: every protected endpoint with no JWT → 401
- [ ] Test: every CO-only endpoint with MLE JWT → 403
- [ ] Test: every MLE-only endpoint with CO JWT → 403
- [ ] Verify Supabase RLS (Row Level Security) policies — regulations and certificates tables have policies matching role

### 4.2 Certificate & Cryptographic Security
- [ ] Verify HMAC signature covers: `cert_id + model_version + regulation_versions + proof_hash` (not just `proof_hash`)
- [ ] Verify `PROOF_CERT_SECRET` is minimum 32 bytes
- [ ] Verify `PROOF_CERT_SECRET` is in `.env`, not hardcoded anywhere — `grep -r "PROOF_CERT_SECRET" src/` should only show reads, never the value
- [ ] Write tamper detection test: modify each field in a certificate, verify each modification is detected

### 4.3 Input Sanitization
- [ ] Verify regulatory text input strips HTML tags before LLM submission
- [ ] Verify regulatory text input rejects inputs > 50,000 characters
- [ ] Verify Z3 formula from LLM is validated before Z3 execution (`validator.py` runs on every extraction)
- [ ] Run `bandit -r src/` — Python security linter, zero high-severity findings

### 4.4 Data Privacy (PII)
- [ ] Audit all `logger.*` calls in `src/` — confirm no applicant PII fields logged
- [ ] Audit `pipeline_events` table — confirm no individual applicant data stored (model-level only)
- [ ] Verify loan approval training data is anonymized before use (hashed IDs only)

### 4.5 Dependency Security
- [ ] Run `poetry run safety check` — zero known CVEs in dependencies
- [ ] Run `npm audit` in `frontend/` — zero high-severity vulnerabilities
- [ ] Pin all direct dependencies to exact versions (already in `pyproject.toml` per TECH.md)
- [ ] Verify `z3-solver==4.12.6.0` is the exact version installed (never auto-upgraded)

### 4.6 Rate Limiting
- [ ] Implement rate limiting middleware on `POST /api/regulations` — 10 req/min per user (AIRULES Rule 35)
- [ ] Test: 11th request within 1 minute → 429 Too Many Requests
- [ ] Verify Railway environment has no public endpoint to bypass FastAPI (no direct DB access)

---

## Stage 5: Testing
*Goal: All CI gates green. Coverage targets met. Every critical path has a test.*

### 5.1 Unit Test Coverage
- [ ] `pipeline/ci/` — bilateral tests (COMPLIANT + VIOLATION) for every Z3 rule check function
- [ ] `pipeline/cd/certificate.py` — certificate generation + HMAC sign + HMAC verify + tamper detection
- [ ] `pipeline/ingestion/approver.py` — all state machine transitions including invalid ones
- [ ] `pipeline/ingestion/validator.py` — valid formulas + malformed formulas
- [ ] `lib/z3_client.py` — prove() + counterexample() with simple test formulas
- [ ] `lib/llm_client.py` — 429 handling, fallback model, retry logic
- [ ] React: `ComplianceBadge` — all 4 statuses, color+text always together
- [ ] React: `useComplianceStatus` — loading, error, all status values
- [ ] Run `poetry run pytest --cov=src --cov-report=term-missing` — verify coverage meets targets from TESTING.md Section 8

### 5.2 Integration Tests
- [ ] `test_certificate_immutability.py` — second write returns 409
- [ ] `test_certificate_hmac_tamper.py` — tampered cert returns 422
- [ ] `test_approval_state_machine.py` — full ingestion → approval → active rule flow
- [ ] `test_ci_gate_failure_halts_pipeline.py` — first gate failure prevents subsequent gates running
- [ ] `test_role_enforcement.py` — MLE cannot approve, CO cannot deploy
- [ ] Run full integration suite against test Supabase + test Neo4j instances

### 5.3 E2E Tests
- [ ] `regulatory_ingestion_flow.spec.ts` — full CO ingestion + two-click approval
- [ ] `ci_gate_violation_display.spec.ts` — submit violating model, verify violation shown to MLE, plain English to CO
- [ ] `proof_certificate_download.spec.ts` — successful deploy → CO downloads certificate
- [ ] Run `npx playwright test` — all 3 flows green

### 5.4 Manual QA Pass
- [ ] Run full TESTING.md Section 6 manual checklist — check every box
- [ ] Verify Z3 smoke test passes: `python scripts/verify_z3_install.py`
- [ ] Verify GitHub Actions CI run is green on `main`

---

## Stage 6: Polish & Deploy
*Goal: Live on Railway. README tells the story. Reviewers can run it in 5 minutes.*

### 6.1 Performance
- [ ] Run Vite bundle analyzer: `npm run build -- --report` — verify initial JS bundle < 400KB gzipped
- [ ] Lazy-load `recharts` (MLE dashboard charts) — not in initial bundle
- [ ] Verify Z3 symbolic check completes in < 500ms per rule on Railway free tier (test against live deployment)
- [ ] Verify full CI pipeline (GitHub Actions) completes in < 10 minutes

### 6.2 Accessibility (CO Interface)
- [ ] Run Lighthouse on CO Dashboard — Accessibility score ≥ 95 (DESIGN.md target)
- [ ] Verify all compliance status displays use color + text + role attribute (never color alone)
- [ ] Verify all form fields have associated `<label>` elements
- [ ] Verify keyboard navigation works for the approve/reject flow
- [ ] Verify `prefers-reduced-motion` is respected — compliance badge transition disabled when set

### 6.3 README
- [ ] Write `README.md` — sections: What is Rego (the innovation), Architecture diagram, Setup in 5 minutes, The Z3 story (why aerospace verification for finance), How to add an RBI rule, How to submit a model, How proof certificates work
- [ ] Add architecture diagram (from TECH.md Section 9) to README
- [ ] Add "The unprecedented comparison table" from PRD.md Section 9 to README — this is the hook
- [ ] Document all GitHub Actions workflows and what triggers them

### 6.4 Railway Deploy
- [ ] Create Railway project — connect to GitHub repo
- [ ] Set all environment variables from `.env.example` in Railway dashboard
- [ ] Set `ENVIRONMENT=production` in Railway
- [ ] Verify FastAPI serves React static build (or configure Railway to serve both)
- [ ] Trigger first deploy — verify `GET /health` returns 200 on live URL
- [ ] Run `python scripts/verify_z3_install.py` against deployed instance — Z3 must work in production
- [ ] Document live URL in README and STATE.md

### 6.5 Demo Preparation
- [ ] Seed live instance with 3 real RBI Master Direction rules from `rbi.org.in`
- [ ] Create demo script: law change → CT trigger → CI gates → certificate → < 3 minutes walkthrough
- [ ] **Railway warm-up** (ISSUES.md ISSUE-003 fix): 5 minutes before demo, run `curl https://[app-name].railway.app/health` to wake the sleeping free-tier instance. Cold start is ~30 seconds — it will break the opening of a timed demo. Add this to your demo checklist as step 0.
- [ ] Prepare the "jaw drop moment": live demo where a regulation change triggers the full pipeline in real time
- [ ] Create test accounts for demo: `demo-co@rego.dev` (compliance officer), `demo-mle@rego.dev` (ML engineer)

**Final acceptance criteria for v1:**
- [ ] Law change to compliant deployment in < 3 minutes (timed)
- [ ] Compliance officer onboards in < 10 minutes with zero coding
- [ ] Proof certificate generated, downloadable, verifiable in < 10 seconds
- [ ] `GET /health/z3` returns Z3 version in production
- [ ] CI pipeline green on `main`
- [ ] No open 🚫 blockers

---

## Dependency Map

```
Stage 1 (Setup)
    ↓
Stage 2 (Core Infrastructure)
    ↓
3.1 Ingestion ──────────────────────────────┐
    ↓                                        │
3.2 Lineage ←── needs 3.1                   │
    ↓                                        │
3.3 CI Gates ←── needs 3.1 + Z3 client     │
    ↓                                        │
3.4 CT ←── needs 3.1 + CI                  │
    ↓                                        │
3.5 CD ←── needs 3.3 + 3.2                 │
    ↓                                        │
3.6 Certificate display ←── needs 3.5      │
    ↓                                        │
3.7 HCI Dashboard ←── needs all 3.1–3.6 ←─┘
    ↓
Stage 4 (Security)
    ↓
Stage 5 (Testing)
    ↓
Stage 6 (Deploy)
```

---

*PLAN.md is the live roadmap. AI updates checkbox states and Current Status block every session.*
*Never mark a step done without verifying its acceptance criteria.*
*Total estimated steps: ~120 checklist items across 6 stages.*
