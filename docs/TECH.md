# TECH.md — Technology Decisions & Stack
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: FINALIZED
# ============================================================
# READ THIS BEFORE: installing any package, adding any service,
# or making any infrastructure decision.
# If it's not in this file — it requires approval first.
# ============================================================

## 0. Stack Philosophy

Every technology choice in Rego answers one question:
**"Does this make compliance a first-class citizen of the pipeline, or does it make it an afterthought?"**

Three non-negotiables that shaped every decision:
1. **Provability over probability** — Z3 SMT Solver for symbolic reasoning, not heuristics
2. **Model-agnostic LLM layer** — OpenRouter prevents vendor lock-in on the most volatile part of the stack
3. **Two interfaces, one API** — React + FastAPI enables proper HCI separation; Streamlit cannot

---

## 1. Complete Stack at a Glance

| Layer | Technology | Version | Why This, Not Something Else |
|-------|-----------|---------|------------------------------|
| **Symbolic Reasoning** | Z3 SMT Solver | `4.12.x` | Mathematical proof certificates. Used in aerospace + military verification. Unbreakable proofs. No other option gives formal guarantees |
| **LLM Layer** | OpenRouter API | latest | Model-agnostic. Single API key. Swap Claude 3.5 Sonnet ↔ GPT-4o without code changes. Free credits cover MVP |
| **Default LLM Model** | Claude 3.5 Sonnet via OpenRouter | `claude-3-5-sonnet` | Best regulatory text → formal logic reasoning. Fallback: `gpt-4o` |
| **ML Framework** | PyTorch | `2.2.x` | Standard for research-grade models. HuggingFace ecosystem |
| **Model Hub** | HuggingFace Transformers | `4.40.x` | Pre-trained regulatory NLP models, model hosting (free tier) |
| **Pipeline Orchestration** | GitHub Actions | — | Free tier, tight Git integration, no infra to manage for MVP |
| **API Backend** | FastAPI | `0.142.x` | Async, auto-generates OpenAPI docs (Swagger), Python-native |
| **Frontend** | React | `18.x` | Two separate interfaces on one API. Drag-and-drop support. Real-time updates via WebSocket |
| **Knowledge Graph** | Neo4j Aura | Free tier | Regulatory version lineage. Law nodes ↔ Model nodes ↔ Proof nodes |
| **Database** | Supabase (PostgreSQL) | latest | Auth + structured data + real-time subscriptions. Free tier |
| **Model Versioning** | MLflow | `2.12.x` | Experiment tracking, model registry, artifact storage |
| **Data Versioning** | DVC | `3.x` | Regulatory document versioning alongside model versioning |
| **Drift / Monitoring** | Evidently AI | `0.4.x` | Model performance monitoring post-deployment |
| **Deployment** | Railway | Free tier | Simple deploys, GitHub integration, free $5/mo credit |
| **Container** | Docker | `24.x` | Reproducible environments for CI gates |
| **Dependency Management** | Poetry | `1.8.x` | Pinned lockfile, deterministic builds |
| **Python Version** | Python | `3.11.x` | Z3, PyTorch, FastAPI all stable on 3.11 |

---

## 2. The Z3 SMT Solver — Why It Changes Everything

Z3 is not a typical ML library. It is a **Satisfiability Modulo Theories (SMT) solver** built by Microsoft Research.

**What it does for Rego:**
- Takes a regulatory rule (e.g. "loan approval model must not use postal code as a feature under RBI Master Directions on Digital Lending 2022") expressed as a formal logic formula
- Takes the model's decision logic expressed as constraints
- Formally **proves** whether the model satisfies the rule — not probabilistically, **mathematically**
- If it cannot prove compliance, it outputs a **counterexample** — the exact scenario where the model violates the rule

**What this means for proof certificates:**
Every Rego proof certificate is backed by a Z3 satisfiability proof. This is the same class of verification used in:
- Boeing 787 flight control software
- Intel CPU formal verification
- Microsoft Azure security proofs
- NASA space mission critical systems

When you tell an auditor: *"This certificate was generated using formal verification — the same technique used to prove fighter jet software is correct"* — the conversation changes.

**Z3 in the pipeline:**
```
Regulatory Rule (formal logic) + Model Constraints
             ↓
        Z3 SMT Solver
             ↓
    UNSAT → Model is compliant (proof found)
    SAT   → Violation detected + counterexample generated
             ↓
    Proof hash stored in certificate
```

**Installation:**
```bash
poetry add z3-solver==4.12.6.0
```

**Never replace Z3 with:** probabilistic checks, LLM-based compliance checking, or heuristic rule matching. Z3 is the non-negotiable foundation of Rego's trust model.

---

## 3. OpenRouter — The Model-Agnostic LLM Layer

**Why OpenRouter, not direct OpenAI/Anthropic API:**

| Problem with direct API | OpenRouter solution |
|------------------------|---------------------|
| GPT-4o deprecated → all code breaks | Swap model string, zero code change |
| Anthropic rate limits hit → pipeline stalls | Automatic fallback to secondary model |
| Vendor raises prices → locked in | Switch model in config file |
| Different APIs for different providers | One unified endpoint for all |

**Configuration:**
```python
# config/llm_config.py
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-3-5-sonnet"
FALLBACK_MODEL = "openai/gpt-4o"
MAX_TOKENS_RULE_EXTRACTION = 2000
TEMPERATURE_RULE_EXTRACTION = 0.1  # Low temp — we want deterministic logic, not creativity
```

**LLM usage scope — CRITICAL:**
The LLM is used **ONLY** for:
1. Regulatory text → formal logic rule extraction (offline, batch)
2. Plain-English violation explanation generation (offline, after Z3 verdict)

The LLM is **NEVER** used for:
- Real-time inference compliance checking (Z3 does this)
- Proof certificate generation (Z3 does this)
- Any step in the hot path of model deployment

**Why:** LLMs hallucinate. Z3 does not. Any compliance decision in the deployment gate must be deterministic and formally verifiable.

---

## 4. Stack by Pipeline Stage

### Regulatory Ingestion
```
Input:  Raw regulatory text (PDF / paste)
Tools:  OpenRouter API → Claude 3.5 Sonnet  (step 1: generate candidate formula)
        ConfidenceScorer                     (step 2: score the candidate — 3 signals)
        Z3                                   (step 3: validate well-formedness)
        Human (CO interface)                 (step 4: approve semantic intent)
        Neo4j Aura                           (step 5: store versioned rule — only after steps 1–4)
        DVC                                  (version the source regulatory document)
Output: Versioned formal logic rule, z3_validated + human_approved, stored in knowledge graph
```

**Confidence Scoring — `pipeline/ingestion/confidence_scorer.py`**

Confidence is calculated in `pipeline/ingestion/confidence_scorer.py` before Z3 validation runs. It gives the CO interface a signal of how much to trust the LLM extraction before a human invests time reviewing it.

```python
# Three signals, one score — deterministic for same inputs
# Final score = completeness(0.5) + z3_valid(0.3) + specificity(0.2)

# Signal 1 — Completeness (weight: 0.5)
# Do the key legal terms from the source text appear in the formula?
# Extracted via spaCy noun chunks + prohibition verbs ("shall not", "must not", "prohibited")
# Score = matched_terms / total_key_terms  (clamped 0.0–1.0)

# Signal 2 — Z3 Structural Validity (weight: 0.3)
# Did Z3 parse_smt2_string() accept the formula without errors?
# Binary: 1.0 if parseable, 0.0 if Z3 raises ParseError or sorts are unresolved
# This signal runs synchronously — no network call

# Signal 3 — Variable Specificity (weight: 0.2)
# Are Z3 variable names meaningful (pin_code_weight) or generic (x1, x2)?
# meaningful = len(var_name) > 2 AND does not match r'^x\d+$'
# Score = min(meaningful_var_count / 3, 1.0)

# Thresholds → UI behavior:
# score >= 0.75 → HIGH:   green badge, normal approve/reject flow
# score >= 0.50 → MEDIUM: amber badge, normal approve/reject flow with warning
# score <  0.50 → LOW:    red badge, extra friction ("I Understand — Review Anyway")
# z3_valid == 0 → REJECTED: formula never shown to CO, extraction error displayed

# ConfidenceResult shape:
# {
#   "score": 0.82,
#   "level": "HIGH",
#   "signals": {
#     "completeness": 0.85,
#     "z3_valid": 1.0,
#     "specificity": 0.75
#   },
#   "recommendation": "High confidence — safe to review and approve"
# }
```



### Continuous Training (CT) — Law Drift Trigger
```
Input:  New rule detected in Neo4j (regulation_version bump)
Tools:  GitHub Actions (trigger CT workflow)
        Kaggle API (push notebook to Kaggle, run on P100 GPU)
        PyTorch + XGBoost (model retraining with constraint_loss)
        MLflow (log new model version, link to regulation version)
        DVC (version training data snapshot)
        Kaggle API (pull retrained model artifact back)
Output: New model candidate registered in MLflow, linked to regulation version
```
**Kaggle CT integration:**
`pipeline/ct/trigger.py` calls the Kaggle API to push and run the training notebook.
The notebook lives at `notebooks/ct_retrain.ipynb` in the repo.
After training completes, GitHub Actions pulls the output via `kaggle kernels output`.
Required env vars: `KAGGLE_USERNAME`, `KAGGLE_KEY` (from kaggle.json).

### Continuous Integration (CI) — Compliance Gates
```
Input:  New model candidate
Tools:  Z3 SMT Solver (symbolic consistency checks vs all active rules)
        PyTorch (performance regression tests)
        Evidently AI (fairness checks, distribution checks)
        GitHub Actions (orchestrates all gates)
Output: PASS → proceed to CD | FAIL → halt + violation report with Z3 counterexample
```

**CI/CT conventions (Stages 3.3 and 3.4)**
- A model is checked from a *bundle* folder under `MODEL_ARTIFACT_DIR`: `profile.json` (`{"weights": {"<feature>_weight": number}}`) and `evaluation.json` (held-out `y_true`, `y_pred`, `baseline_y_pred`, `groups`). A feature missing from the profile counts as weight 0.
- Rules are SMT-LIB2 (`declare-const` + `assert`) stating the condition a compliant model must meet. Z3 looks for a way the rule can be false under the model's weights: UNSAT proves compliance, SAT gives a counterexample.
- Gates fail closed: no active rules, an unparseable rule, an UNKNOWN Z3 answer, missing evaluation data, or a crashing gate all count as a violation. The first failure halts the run.
- `reg_attack` is a boundary-robustness test: each weight a rule mentions is nudged by +/-0.1% and the rule re-proved. Fairness is a demographic-parity gap (max 10 points); regression is F1 not more than 5% below baseline. Both are pure Python.
- `ci/reporter.py` uses templates, not an LLM (no LLM runs in `pipeline/ci/`).
- `ct/trigger.py` dispatches the GitHub Actions workflow; `ct/kaggle_runner.py` drives Kaggle through the `kaggle` CLI. The CT notebook excludes prohibited features (hard zero weight); `ct/constraint_loss.py` holds the PyTorch penalty for a neural-network model.
- `mlflow` and `kaggle` live in the optional Poetry group `ct` (`poetry install --with ct`). Extra environment variables: `MODEL_ARTIFACT_DIR`, `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `CT_WORKFLOW_FILE`, `CT_WORKFLOW_REF`, `KAGGLE_USERNAME`, `KAGGLE_KEY`, `KAGGLE_TRAIN_DATASET`.

### Continuous Deployment (CD)
```
Input:  CI-passed model
Tools:  FastAPI (serving endpoint)
        Docker (containerized deployment)
        Railway (zero-downtime deploy)
        Z3 (final proof hash generation)
        Supabase (store proof certificate record)
Output: Deployed model + proof certificate (model_version + regulation_versions + z3_proof_hash)
```

**CD conventions (Stage 3.5)**
- `POST /api/pipeline/deploy` (ML engineer only) refuses unless the latest CI result for every gate is compliant in `pipeline_events`. It then re-proves every active rule with Z3 against the model bundle, writes the certificate once, records lineage, runs a canary with a shadow Z3 check, and promotes. There is no override.
- `proof_hash` is a SHA-256 over the model bundle hash and the (version, rule, formula hash) of every active rule. It is deterministic, so deploying the same model against the same rules twice hits the unique constraint and returns 409. A new regulation version gives a new hash and so a new certificate.
- `hmac_signature` covers model version, regulation versions and proof hash, keyed with `PROOF_CERT_SECRET`. Every read re-verifies it; a failing certificate returns 422 from `GET /certificates/{id}` and is listed as `tampered` (hash and signature blanked).
- There is no create, update or delete certificate route. Compliance officers do not see proof hashes on screen; the downloaded JSON includes them for auditors.
- The Railway deployer sets `MODEL_VERSION` on a canary service, then on the main service, and redeploys. Railway cannot split traffic by percentage, so the canary takes no live traffic. Its GraphQL calls are untested against a live project. Variables: `RAILWAY_API_TOKEN`, `RAILWAY_PROJECT_ID`, `RAILWAY_ENVIRONMENT_ID`, `RAILWAY_SERVICE_ID`, `RAILWAY_CANARY_SERVICE_ID`.

**Certificate display and verification (Stage 3.6)**
- `POST /api/certificates/verify` takes `{cert_id, proof_hash}` and returns `{valid, explanation}`. It needs no login, which is a deliberate exception to the login requirement. It re-verifies the HMAC first, so a certificate whose database row was edited is never reported valid. Rate limiting for it is planned for Stage 4.6.
- `ProofCertificateView` is shared. The ML engineer sees the full proof hash. The compliance officer does not but can copy it to the clipboard with "Copy hash" to hand to an auditor.
- `scripts/generate_dev_certificate.py` signs a `dev-<timestamp>` certificate for UI work. It prints JSON by default; `--insert` writes through the normal write-once path and is refused when `ENVIRONMENT=production`.

### HCI Dashboard
```
Backend:  FastAPI (REST + WebSocket for real-time status)
Frontend: React 18 (two interfaces: compliance officer + ML engineer)
Auth:     Supabase Auth (role-based: compliance_officer | ml_engineer | cto)
DB:       Supabase PostgreSQL (pipeline events, certificate records, user sessions)
Graph:    Neo4j Aura (lineage queries — "which law was this model compliant with?")
```

---

**Dashboards and HCI principles (Stage 3.7)**
- Both dashboards read `pipeline_events` through Supabase Realtime (migration 07 adds the table to the `supabase_realtime` publication; row level security still applies). The compliance status is derived in the browser by `deriveComplianceStatus` from the latest gate event, the latest intact certificate and the rules in force. A violation newer than the latest certificate turns it red; rules not covered by the latest certificate make it amber.
- The compliance officer interface shows no rule IDs, hashes or Z3 terms. Rules appear as "RBI section 4.1, version of 7 Oct 2026". The exact condition of a rule is rendered in words by `readableRule`, a deterministic translator (not an LLM) that returns nothing for logic it cannot express, so the officer can check the AI's summary against the real condition.
- `GET /api/pipeline/drift-log` and `GET /api/models/diff` (ML engineer and CTO) back the MLE dashboard and Model Diff page. A diff change is compliance-impacting when its feature appears in an active rule.

| Principle | Where it is enforced | Check |
|-----------|---------------------|-------|
| Visibility | `deriveComplianceStatus` always yields plain-English text; the hero is a live region with colour, icon and label | `complianceStatus.test.ts` |
| Control | `approver.transition` refuses approve/reject without a human flag; UI needs two deliberate actions | `test_approver.py`, `test_service.py` |
| Feedback | every gate returns a plain-English result that is streamed and stored | `test_gates.py`, `test_gate_runner.py` |
| Error Prevention | the only caller of the deployer is `cd/canary.py`, inside `deploy_model`, which checks CI, then Z3, then writes the certificate, then runs the canary; no function takes a bypass argument | `test_no_bypass.py`, `test_deploy.py` |
| Accessibility | separate role-gated routes and separate API roles for each interface | `require_role` on every route; no browser accessibility audit yet (Stage 6.2) |

Error Prevention covers Rego's own deploy path. Someone with Railway access can still redeploy a service by hand outside Rego.

**Security conventions (Stage 4)**
- Missing, malformed or unknown credentials are always a 401 with the same body and no detail. A signed-in user with the wrong role gets a 403. `tests/integration/test_auth_matrix.py` lists every route with the roles allowed and fails if a route is added without an entry.
- `POST /regulations` is limited to 10 requests a minute per signed-in user and `POST /certificates/verify` to 30 a minute per client address (`src/api/rate_limit.py`, in-process, so single instance). The limit runs after authentication so it is keyed on a real user. It is a dependency, not middleware, because middleware cannot know the user without authenticating twice.
- The certificate HMAC covers the certificate id, model version, regulation versions and proof hash. `PROOF_CERT_SECRET` must be at least 32 bytes; shorter is refused when signing and when verifying.
- The regulation `section` is limited to letters, digits and `. ( ) _ -` because it reaches the LLM prompt. The text is stripped of HTML tags and control characters and capped at 50,000 characters.
- Row level security (`supabase/migrations/08_tighten_rls.sql`): the anon role has no table access; signed-in staff can read only; the API (service key) does all writes; certificates cannot be updated or deleted by any role, including the service role. Auditors use the verify endpoint, not the database. The migration has not been run against a real Supabase project; test each role through PostgREST after applying it.
- No applicant PII exists in the code or database: a test scans every log call for PII and credential words, `pipeline_events` stores model-level columns only, and the training notebook refuses personal data columns or unhashed id columns.
- Dependencies: CI runs `bandit` (medium and above), `scripts/audit_lock.py` (all groups in `poetry.lock`, via `pip-audit`) and `npm audit --omit=dev --audit-level=high`. `bandit` and `pip-audit` are dev tools added in Stage 4; `pip-audit` replaces `safety`, which now needs an account. Advisories we accept are listed with reasons in `scripts/audit_lock.py`.
- Frontend: react-router-dom 7, vite 8, vitest 5, @vitejs/plugin-react 6 and jsdom 29 need Node 22 (the CI jobs and the Docker build stage use it) and @types/node 22. `npm audit --omit=dev` reports no vulnerabilities. tailwindcss 4 (with `@tailwindcss/postcss` and tailwind-merge 3) is applied, so `npm audit` reports no vulnerabilities at all. Tailwind 4 needs Chrome 111, Safari 16.4 or Firefox 128 or newer. The dev server binds to localhost only.
- Not covered by code: Railway must not expose the database or Neo4j publicly, and the Supabase anon key is public by design, so RLS is the only protection for direct database access. Check both when deploying (Stage 6.4).

**Test tooling (Stage 5)**
- Python: `pytest` with `pytest-cov`; unit tests sit beside the code, flow tests are in `tests/integration/`. `tests/integration/world.py` is an in-memory Neo4j, Supabase and Railway that behaves like the real ones for the queries this code sends, so whole flows (ingest, approve, run the gates, deploy, certify, tamper) run through the real API code. It fails loudly on a query it does not recognise. Coverage is enforced at 90% (`pyproject.toml`); CI runs `pytest --cov`.
- Frontend unit tests: `vitest` with `jsdom`, `@testing-library/react`, `@testing-library/jest-dom` and `@testing-library/user-event`. These are the tools the templates in `docs/TESTING.md` use, added to `devDependencies` in Stage 5.
- End-to-end: `@playwright/test` (listed above) drives the real frontend in the Chrome that is already installed (`channel: 'chrome'`, override with `E2E_BROWSER_CHANNEL`), so no browser is downloaded. The API and Supabase are stubbed in `frontend/tests/e2e/support.ts`. These tests prove the browser behaviour; they do not prove the backend, a real login, or Supabase Realtime.
- `tests/integration/test_frontend_backend_constants.py` fails if the status constants in `constants.ts` drift from the Pydantic enums or the database enum.

**Deployment shape and accessibility (Stage 6)**
- One container serves the API and the built web app. The API is under `/api`; `/health/` is also served at the root for the platform health check. Any other path returns `index.html`, so deep links and reloads work, while an unknown `/api` path stays a 404. The web app is built with `VITE_API_BASE_URL=/api`, so it needs no CORS and the WebSocket address is derived from the page origin (`socketUrl.ts`).
- The image has three stages (build the frontend, install runtime Python dependencies with `poetry install --only main`, runtime as a non-root user). See `docs/DEPLOY.md`. CI builds the image and probes the running container.
- Pages are loaded on first use (`React.lazy`), which brought the initial JavaScript from 173 KB to 122 KB gzipped. `recharts` is listed as a dependency but no chart exists yet, so it is not in any bundle.
- Accessibility is checked with axe-core through Playwright (`frontend/tests/e2e/accessibility.spec.ts`): WCAG 2.0 and 2.1 A and AA rules on every page for both roles, the review card steps, form errors, keyboard-only approval, and reduced motion. This is the engine behind the Lighthouse accessibility score, but Lighthouse itself has not been run. The audit found and fixed low-contrast small text, an unlabelled file input, white-on-green buttons below 4.5:1 contrast, and missing reduced-motion handling.
- `@axe-core/playwright` is a dev dependency added for this audit.

**Model file storage**
- `src/lib/model_bundle.py` reads bundles through a `BundleSource`: `LocalBundleSource` (a folder, for development) or `SupabaseBundleSource` (a private Storage bucket, the production default through `MODEL_BUNDLE_STORE`). Both give the same hash for the same files, so a certificate does not depend on where the files were kept.
- Bundle names are limited to letters, digits and `. _ -` and may not be only dots, so a name cannot address another path. Each file is capped at 50 MB.
- Each CI result stores `bundle_hash`, the SHA-256 of the files it checked (migration 09 adds the column). `confirm_ci_passed` refuses a deploy unless all four gates passed on the bytes being deployed, and results recorded without a hash are refused. This stops a bundle being swapped in storage after it passed.
- Storage failures raise `BundleStorageError` and the API answers 503 with a plain message. Storage calls run in a worker thread so they do not block the server.
- The Storage calls were tested against a stand-in for the client. Their method signatures and option keys (`content-type`, `upsert`) were checked against the installed supabase-py 2.32. They have not been run against a real bucket.

## 5. Pinned Versions (Lockfile)

These are the approved versions. Do not upgrade without updating this file and re-running full CI.

```toml
# pyproject.toml - every direct dependency is pinned exactly (Stage 4.5)
[tool.poetry.dependencies]
python = "^3.11"
z3-solver = "4.12.6.0"
fastapi = "0.142.2"
uvicorn = "0.29.0"
python-dotenv = "1.2.4"
neo4j = "5.28.7"
supabase = "2.32.0"
openai = "1.109.1"
pydantic = "2.13.5"
httpx = "0.27.2"

[tool.poetry.group.dev.dependencies]
pytest = "9.0.3"
pytest-asyncio = "1.4.0"
pytest-cov = "5.0.0"
black = "26.3.1"
ruff = "0.4.10"
bandit = "1.9.4"
pip-audit = "2.10.1"
mypy = "1.20.2"

# optional group: poetry install --with ct
[tool.poetry.group.ct.dependencies]
mlflow = "3.15.0"
kaggle = "1.8.4"
```

```json
// package.json — frontend key dependencies
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^7.18.0",
    "axios": "^1.6.0",
    "react-dropzone": "^14.2.0",
    "@tanstack/react-query": "^5.36.0",
    "zustand": "^4.5.0",
    "recharts": "^2.12.0",
    "tailwindcss": "^4.3.0",
    "@tailwindcss/postcss": "^4.3.0"
  },
  "devDependencies": {
    "vite": "^8.3.0",
    "typescript": "^5.4.0",
    "@types/react": "^18.3.0",
    "vitest": "^5.0.0",
    "eslint": "^9.2.0",
    "@playwright/test": "^1.44.0"
  }
}
```

---

## 6. Forbidden Packages ⛔

Do not install these. No exceptions without PRD + TECH.md update.

| Package | Why Forbidden |
|---------|--------------|
| `scikit-learn` as primary model | PyTorch only — symbolic layer needs tensor-level model introspection |
| Any probabilistic logic library replacing Z3 | Z3 is the trust foundation — probabilistic compliance is not compliance |
| `celery` / `redis` | Over-engineered for MVP — GitHub Actions handles orchestration |
| `kubernetes` / `helm` | Out of scope for MVP infra |
| `langchain` | Adds abstraction over OpenRouter without benefit; use OpenAI SDK directly with OpenRouter base URL |
| Any LLM in the deployment hot path | LLM is offline/batch only — never in CI gate or CD gate |
| `streamlit` | PRD committed to React for HCI reasons — Streamlit not permitted |
| `gradio` | Same reason as Streamlit |
| Any package not in pyproject.toml lockfile | Add to TECH.md first, get approval, then install |

---

## 7. Environment Variables

```bash
# .env — never commit this file
# .env.example — commit this, update when adding new vars

# LLM
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_DEFAULT_MODEL=anthropic/claude-3-5-sonnet
LLM_FALLBACK_MODEL=openai/gpt-4o

# Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...    # backend only, never expose to frontend

# Graph
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...

# MLflow
MLFLOW_TRACKING_URI=./mlruns   # local for MVP
MLFLOW_EXPERIMENT_NAME=rego-compliance

# App
ENVIRONMENT=development        # development | staging | production
LOG_LEVEL=INFO
PROOF_CERT_SECRET=...          # HMAC secret for certificate signing
```

**Rules:**
- Every new env var must be added to `.env.example` immediately
- `SUPABASE_SERVICE_KEY` never reaches the React frontend — backend only
- `PROOF_CERT_SECRET` rotates on every production deploy
- CI reads secrets from GitHub Actions Secrets — never from committed files

---

## 8. MVP Jurisdiction Decision

**Chosen for v1: India — RBI Master Directions on Digital Lending (2022) + Fair Practices Code**

Rationale:
- Directly relevant — India-based project, real RBI circulars publicly available at rbi.org.in (no paywalls)
- RBI Master Directions on Digital Lending (Aug 2022) directly governs algorithmic loan approval models
- Fair Practices Code mandates explainability of credit decisions — maps exactly to Rego's proof certificates
- More impressive to Indian reviewers than generic references — shows domain awareness
- India RBI + RBI Fair Practices Code deferred to v2

---

## 9. Architecture Diagram (High-Level)

```
┌─────────────────────────────────────────────────────────┐
│                    REGO PLATFORM                         │
│                                                         │
│  ┌──────────────┐    ┌──────────────────────────────┐  │
│  │  React       │    │        FastAPI                │  │
│  │  Dashboard   │◄──►│  /api/regulations             │  │
│  │              │    │  /api/pipeline                │  │
│  │  [CO View]   │    │  /api/certificates            │  │
│  │  [MLE View]  │    │  /api/models                  │  │
│  └──────────────┘    └──────────┬───────────────────┘  │
│                                  │                       │
│         ┌────────────────────────┼───────────────┐      │
│         ▼                        ▼               ▼      │
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │  Supabase   │  │  Neo4j Aura     │  │  MLflow      ││
│  │  (users,    │  │  (law↔model     │  │  (model      ││
│  │   events,   │  │   lineage       │  │   registry)  ││
│  │   certs)    │  │   graph)        │  │              ││
│  └─────────────┘  └─────────────────┘  └──────────────┘│
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              CI/CD/CT PIPELINE                    │  │
│  │                                                   │  │
│  │  OpenRouter──►LLM──►Z3 Validate──►Neo4j Store    │  │
│  │  (rule extraction)   (well-formed?)  (version)    │  │
│  │                                                   │  │
│  │  GitHub Actions──►Z3 Gates──►Docker──►Railway     │  │
│  │  (orchestration)  (CI checks)  (build) (deploy)   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Local Development Setup

```bash
# 1. Clone and install
git clone https://github.com/your-org/rego-mlops
cd rego-mlops
poetry install

# 2. Frontend
cd frontend && npm install && cd ..

# 3. Environment
cp .env.example .env
# Fill in OPENROUTER_API_KEY, SUPABASE_URL, NEO4J_URI

# 4. Start backend
poetry run uvicorn src.api.main:app --reload --port 8000

# 5. Start frontend
cd frontend && npm run dev   # Vite → http://localhost:5173

# 6. Verify Z3 works
poetry run python -c "import z3; s = z3.Solver(); print('Z3 OK:', z3.get_version_string())"

# 7. Run CI gates locally
poetry run pytest tests/ --cov=src --cov-report=term-missing
```

---

*TECH.md is FINALIZED. Any package, service, or infrastructure change requires updating this file FIRST before implementation.*
