# ARCHITECTURE.md — File Placement Law
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: FINALIZED
# ============================================================
# This file is FILE PLACEMENT LAW.
# Before creating any file, read this.
# If it's not in this structure — ask before creating it.
# Wrong file placement breaks the three-layer separation
# that is the architectural foundation of Rego.
# ============================================================

## 0. Architectural Philosophy — Three Layers, Zero Overlap

Rego's architecture maps directly to how the product works:

```
┌─────────────────────────────────────────────────────┐
│  LAYER 1: /features/   — What humans see & interact │
│  Two interfaces. Same API. Zero shared components.  │
├─────────────────────────────────────────────────────┤
│  LAYER 2: /pipeline/   — Where the magic happens    │
│  ingestion → ci → ct → cd. Each stage is isolated.  │
├─────────────────────────────────────────────────────┤
│  LAYER 3: /lib/        — Infrastructure clients     │
│  Z3, OpenRouter, Neo4j, MLflow. No business logic.  │
└─────────────────────────────────────────────────────┘
```

**The rule:** Features don't import from pipeline. Pipeline doesn't import from features.
Both import from lib. Lib imports from nothing inside this project.
Violations of this rule break the separation that makes Rego auditable.

---

## 1. Full Folder Structure

```
rego-mlops/
│
├── src/                          # All Python backend source
│   │
│   ├── api/                      # FastAPI application
│   │   ├── main.py               # App entry point, router registration
│   │   ├── dependencies.py       # Shared FastAPI dependencies (auth, db)
│   │   ├── middleware.py         # CORS, logging, request ID injection
│   │   │
│   │   ├── routes/               # One router file per domain
│   │   │   ├── regulations.py    # POST /regulations, GET /regulations/{id}
│   │   │   ├── pipeline.py       # GET /pipeline/status, POST /pipeline/trigger
│   │   │   ├── certificates.py   # GET /certificates/{id}, POST /certificates/verify
│   │   │   ├── models.py         # GET /models, GET /models/{version}/diff
│   │   │   └── health.py         # GET /health, GET /health/z3
│   │   │
│   │   └── schemas/              # Pydantic request/response models
│   │       ├── regulation.py     # RegulationCreate, RegulationRead, RuleLogic
│   │       ├── certificate.py    # ProofCertificate, CertificateVerify
│   │       ├── pipeline.py       # PipelineStatus, PipelineEvent, GateResult
│   │       └── model.py          # ModelVersion, ModelDiff, ComplianceScore
│   │
│   ├── pipeline/                 # LAYER 2 — CI/CD/CT stages (core innovation)
│   │   │
│   │   ├── ingestion/            # Regulatory Ingestion Engine
│   │   │   ├── __init__.py
│   │   │   ├── extractor.py      # LLM → formal logic rule extraction
│   │   │   ├── validator.py      # Z3 well-formedness check on extracted rules
│   │   │   ├── versioner.py      # Rule versioning, Neo4j storage
│   │   │   ├── approver.py       # Human approval state machine
│   │   │   └── tests/
│   │   │       ├── test_extractor.py
│   │   │       ├── test_validator.py
│   │   │       └── fixtures/
│   │   │           └── rbi_sample_circular.txt   # Real RBI text for tests
│   │   │
│   │   ├── ci/                   # Continuous Integration gates
│   │   │   ├── __init__.py
│   │   │   ├── gate_runner.py    # Orchestrates all CI gates in sequence
│   │   │   ├── symbolic_check.py # Z3 consistency: model vs ALL active rules
│   │   │   ├── reg_attack.py     # RegAttack adversarial regulatory tests
│   │   │   ├── fairness_check.py # Fairness gate (demographic parity, etc.)
│   │   │   ├── regression.py     # Statistical performance regression gate
│   │   │   ├── reporter.py       # Violation report: rule_id + plain English
│   │   │   └── tests/
│   │   │       ├── test_symbolic_check.py
│   │   │       ├── test_reg_attack.py
│   │   │       └── test_gate_runner.py
│   │   │
│   │   ├── ct/                   # Continuous Training — law drift trigger
│   │   │   ├── __init__.py
│   │   │   ├── drift_detector.py # Detects new/amended rules in knowledge graph
│   │   │   ├── trigger.py        # Law drift → GitHub Actions workflow dispatch
│   │   │   ├── trainer.py        # PyTorch retraining with compliance constraints
│   │   │   ├── constraint_loss.py# Custom loss term encoding regulatory constraints
│   │   │   └── tests/
│   │   │       ├── test_drift_detector.py
│   │   │       └── test_trainer.py
│   │   │
│   │   └── cd/                   # Continuous Deployment
│   │       ├── __init__.py
│   │       ├── deployer.py       # Zero-downtime Railway deploy orchestration
│   │       ├── canary.py         # Canary release + shadow compliance testing
│   │       ├── certificate.py    # Proof certificate generation (Z3 hash + metadata)
│   │       ├── lineage.py        # Links model_version ↔ regulation_versions in Neo4j
│   │       └── tests/
│   │           ├── test_certificate.py
│   │           └── test_lineage.py
│   │
│   ├── lib/                      # LAYER 3 — Infrastructure clients (no business logic)
│   │   ├── z3_client.py          # Z3 SMT Solver wrapper — prove(), counterexample()
│   │   ├── llm_client.py         # OpenRouter client — extract_rules(), explain()
│   │   ├── neo4j_client.py       # Neo4j Aura — graph queries, lineage writes
│   │   ├── mlflow_client.py      # MLflow — log_model(), get_version(), link_regulation()
│   │   ├── supabase_client.py    # Supabase — auth, events, certificate records
│   │   ├── evidently_client.py   # Evidently AI — drift reports, fairness metrics
│   │   └── tests/
│   │       ├── test_z3_client.py
│   │       └── test_llm_client.py
│   │
│   └── models/                   # ML model definitions (PyTorch)
│       ├── loan_approval/
│       │   ├── model.py          # LoanApprovalModel(nn.Module)
│       │   ├── dataset.py        # RBILoanDataset(Dataset)
│       │   ├── features.py       # Feature definitions (what the model sees)
│       │   └── tests/
│       │       └── test_model.py
│       └── base.py               # BaseRegoModel — compliance_constraints property
│
├── frontend/                     # React 18 + TypeScript + Vite
│   │
│   ├── src/
│   │   │
│   │   ├── features/             # LAYER 1 — Two interfaces, zero cross-import
│   │   │   │
│   │   │   ├── compliance-officer/   # Non-technical interface
│   │   │   │   ├── pages/
│   │   │   │   │   ├── Dashboard.tsx      # Live compliance status
│   │   │   │   │   ├── RegulationUpload.tsx # Drag-and-drop regulatory text
│   │   │   │   │   ├── ApprovalQueue.tsx   # Approve/reject LLM rule translations
│   │   │   │   │   └── Certificates.tsx   # Download + verify proof certificates
│   │   │   │   ├── components/
│   │   │   │   │   ├── ComplianceBadge.tsx     # GREEN/RED status in plain English
│   │   │   │   │   ├── RuleTranslationCard.tsx # LLM output → approve/reject UI
│   │   │   │   │   ├── RegulationDropzone.tsx  # react-dropzone integration
│   │   │   │   │   └── ProofCertificateView.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   ├── useComplianceStatus.ts
│   │   │   │   │   └── useCertificates.ts
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   │   ├── ml-engineer/          # Technical interface
│   │   │   │   │   ├── pages/
│   │   │   │   │   │   ├── PipelineMonitor.tsx    # Live CI/CD/CT pipeline status
│   │   │   │   │   │   ├── ViolationReport.tsx    # Z3 counterexample + rule trace
│   │   │   │   │   │   ├── ModelDiff.tsx          # Visual diff between model versions
│   │   │   │   │   │   └── ModelRegistry.tsx      # MLflow model versions + lineage
│   │   │   │   │   ├── components/
│   │   │   │   │   │   ├── Sidebar.tsx            # Fixed sidebar 240px
│   │   │   │   │   │   ├── GateStatusRow.tsx      # CI gate: PASS/FAIL + details
│   │   │   │   │   │   ├── RuleViolationDetail.tsx # Exact rule_id + counterexample
│   │   │   │   │   │   ├── LineageGraph.tsx        # model ↔ regulation lineage viz
│   │   │   │   │   │   └── PipelineTimeline.tsx
│   │   │   │   │   ├── hooks/
│   │   │   │   │   │   ├── usePipelineStatus.ts
│   │   │   │   │   │   └── useModelVersions.ts
│   │   │   │   │   └── index.ts
│   │   │
│   │   ├── lib/                  # Shared frontend utilities
│   │   │   ├── api/
│   │   │   │   ├── client.ts     # Axios instance with auth headers
│   │   │   │   ├── regulations.ts
│   │   │   │   ├── pipeline.ts
│   │   │   │   ├── certificates.ts
│   │   │   │   └── models.ts
│   │   │   ├── auth/
│   │   │   │   ├── supabase.ts   # Supabase client init
│   │   │   │   └── useAuth.ts    # Auth hook — role: compliance_officer | ml_engineer
│   │   │   ├── ws/
│   │   │   │   └── pipelineSocket.ts  # WebSocket for real-time pipeline events
│   │   │   └── utils/
│   │   │       ├── formatters.ts  # Date, duration, compliance score formatting
│   │   │       └── constants.ts   # RBI regulation IDs, gate names, status enums
│   │   │
│   │   ├── components/           # Shared UI primitives only
│   │   │   ├── ui/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Badge.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── StatusDot.tsx
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   └── layout/
│   │   │       ├── RootLayout.tsx     # Role-based layout switcher
│   │   │       ├── COLayout.tsx       # Compliance officer shell
│   │   │       └── MLELayout.tsx      # ML engineer shell
│   │   │
│   │   ├── router/
│   │   │   └── index.tsx         # react-router-dom: role → interface routing
│   │   │
│   │   ├── store/
│   │   │   └── pipelineStore.ts  # Zustand: live pipeline state
│   │   │
│   │   ├── types/
│   │   │   ├── regulation.ts
│   │   │   ├── certificate.ts
│   │   │   ├── pipeline.ts
│   │   │   └── model.ts
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── tailwind.config.ts
│
├── .github/
│   └── workflows/
│       ├── ci.yml                # Runs Z3 gates + tests on every PR
│       ├── ct.yml                # Triggered by regulation_version bump in Neo4j
│       └── cd.yml                # Deploys to Railway on CI pass
│
├── tests/                        # Integration + E2E tests only
│   ├── integration/
│   │   ├── test_pipeline_e2e.py  # Full ingestion → CI → CD flow
│   │   └── test_certificate_verify.py
│   └── fixtures/
│       └── rbi_master_directions_2022_excerpt.txt
│
├── scripts/
│   ├── poc_pipeline.py           # Stage 0 proof of concept — run this first
│   ├── seed_rbi_rules.py         # Seeds initial RBI rules into Neo4j
│   ├── verify_z3_install.py      # Smoke test: Z3 can prove a simple formula
│   └── generate_dev_certificate.py  # Generate a test proof certificate locally
│
├── notebooks/
│   └── ct_retrain.ipynb          # Kaggle CT retraining notebook (runs on P100 GPU)
│                                 # Triggered by pipeline/ct/trigger.py via Kaggle API
│                                 # Input: regulation_version + training data path
│                                 # Output: model.pkl → registered in MLflow
│
├── docs/
│   ├── PRD.md
│   ├── TECH.md
│   ├── ARCHITECTURE.md           ← this file
│   ├── DESIGN.md
│   └── TESTING.md
│
│
├── pyproject.toml
├── poetry.lock
├── .env.example
├── .env                          # NEVER commit
├── .gitignore
├── Dockerfile
├── docker-compose.yml            # Local dev: FastAPI + Neo4j + Supabase local
└── README.md
```

---

## 2. File Placement Rules

| Type of file | Goes in | Example |
|---|---|---|
| FastAPI route handler | `src/api/routes/` | `regulations.py` |
| Pydantic schema | `src/api/schemas/` | `certificate.py` |
| Pipeline stage logic | `src/pipeline/{stage}/` | `pipeline/ci/symbolic_check.py` |
| Infrastructure client | `src/lib/` | `z3_client.py`, `llm_client.py` |
| ML model definition | `src/models/{model_name}/` | `models/loan_approval/model.py` |
| React page component | `frontend/src/features/{interface}/pages/` | `compliance-officer/pages/Dashboard.tsx` |
| React feature component | `frontend/src/features/{interface}/components/` | `ml-engineer/components/GateStatusRow.tsx` |
| Shared UI primitive | `frontend/src/components/ui/` | `Badge.tsx`, `Button.tsx` |
| API client function | `frontend/src/lib/api/` | `certificates.ts` |
| Shared type (frontend) | `frontend/src/types/` | `certificate.ts` |
| GitHub Actions workflow | `.github/workflows/` | `ci.yml` |
| Integration test | `tests/integration/` | `test_pipeline_e2e.py` |
| Unit test (Python) | Colocated in `tests/` subfolder next to source | `pipeline/ci/tests/test_symbolic_check.py` |
| Unit test (React) | Colocated next to component | `Dashboard.test.tsx` |
| One-off script | `scripts/` | `seed_rbi_rules.py` |
| Test fixture / sample data | `tests/fixtures/` or `pipeline/{stage}/tests/fixtures/` | `rbi_sample_circular.txt` |

**One rule above all:** Features (`/features/`) never import from pipeline (`/pipeline/`). Pipeline never imports from features. Both import from lib. Lib imports from nothing internal.

---

## 3. Naming Conventions

### Python (backend)
| Thing | Convention | Example |
|-------|-----------|---------|
| Files | `snake_case.py` | `symbolic_check.py` |
| Classes | `PascalCase` | `Z3ComplianceChecker` |
| Functions | `snake_case` | `extract_rules_from_text()` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_RULE_EXTRACTION_TOKENS` |
| Test files | `test_{module}.py` | `test_symbolic_check.py` |
| Private functions | `_snake_case` | `_parse_z3_output()` |

### TypeScript / React (frontend)
| Thing | Convention | Example |
|-------|-----------|---------|
| Component files | `PascalCase.tsx` | `ComplianceBadge.tsx` |
| Hook files | `camelCase.ts` prefixed `use` | `useComplianceStatus.ts` |
| Utility files | `camelCase.ts` | `formatters.ts` |
| Type files | `camelCase.ts` | `certificate.ts` |
| CSS/style files | `PascalCase.module.css` | `Dashboard.module.css` |

### Domain-specific naming (use these everywhere, no synonyms)
| Concept | Always call it | Never call it |
|---------|---------------|---------------|
| A regulatory rule in formal logic | `rule` | `policy`, `constraint`, `law` |
| The Z3 proof result | `proof` | `result`, `output`, `check` |
| The deployment artifact | `certificate` | `report`, `badge`, `token` |
| Law drift detection | `regulation_drift` | `data_drift`, `law_change` |
| The compliance check stage | `symbolic_check` | `logic_check`, `rule_check` |
| Law version + model version pair | `lineage` | `history`, `trace`, `log` |

---

## 4. Data Flow

```
                        ┌─────────────────┐
                        │  Compliance     │
                        │  Officer (UI)   │
                        └────────┬────────┘
                                 │ drag-drop regulatory text
                                 ▼
                    ┌────────────────────────┐
                    │  pipeline/ingestion/   │
                    │  extractor.py          │  ← OpenRouter/LLM
                    │  validator.py          │  ← Z3 (well-formed?)
                    │  approver.py           │  ← CO clicks approve
                    │  versioner.py          │  ← Neo4j write
                    └────────────┬───────────┘
                                 │ regulation_version bumped
                                 ▼
                    ┌────────────────────────┐
                    │  pipeline/ct/          │
                    │  drift_detector.py     │  ← watches Neo4j
                    │  trigger.py            │  ← dispatches GH Actions
                    │  trainer.py            │  ← PyTorch retrain
                    └────────────┬───────────┘
                                 │ new model candidate
                                 ▼
                    ┌────────────────────────┐
                    │  pipeline/ci/          │
                    │  symbolic_check.py     │  ← Z3 (UNSAT = compliant)
                    │  reg_attack.py         │  ← adversarial tests
                    │  fairness_check.py     │  ← Evidently AI
                    │  regression.py         │  ← performance gate
                    └────────────┬───────────┘
                                 │ ALL gates pass
                                 ▼
                    ┌────────────────────────┐
                    │  pipeline/cd/          │
                    │  canary.py             │  ← shadow testing
                    │  certificate.py        │  ← Z3 proof hash
                    │  lineage.py            │  ← Neo4j: model↔law link
                    │  deployer.py           │  ← Railway zero-downtime
                    └────────────┬───────────┘
                                 │
                    ┌────────────▼───────────┐
                    │  PRODUCTION            │
                    │  Model deployed        │
                    │  Certificate in        │
                    │  Supabase              │
                    └────────────────────────┘
                                 │
                    ┌────────────▼───────────┐
                    │  ML Engineer (UI)      │  ← reads pipeline events
                    │  CO Dashboard (UI)     │  ← reads compliance status
                    └────────────────────────┘
```

**Read/Write summary:**

| Component | Reads from | Writes to |
|-----------|-----------|-----------|
| `ingestion/extractor.py` | OpenRouter API | — |
| `ingestion/versioner.py` | — | Neo4j (rule nodes) |
| `ct/drift_detector.py` | Neo4j | GitHub Actions (trigger) |
| `ct/trainer.py` | HuggingFace, DVC | MLflow (model version) |
| `ci/symbolic_check.py` | Neo4j (rules), MLflow (model) | — |
| `cd/certificate.py` | MLflow, Neo4j | Supabase (cert record) |
| `cd/lineage.py` | MLflow, Supabase | Neo4j (lineage edges) |
| FastAPI routes | Supabase, Neo4j, MLflow | Supabase (events) |
| React frontend | FastAPI (REST + WS) | FastAPI (POST actions) |

---

## 5. Path Aliases

### Python (pyproject.toml + import style)
```toml
# pyproject.toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```
```python
# Import style — always absolute from src/
from pipeline.ci.symbolic_check import Z3ComplianceChecker
from lib.z3_client import Z3Client
from api.schemas.certificate import ProofCertificate
# Never: from ../../lib.z3_client import ...
```

### TypeScript (tsconfig.json + vite.config.ts)
```json
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/features/*": ["src/features/*"],
      "@/pipeline/*": ["src/pipeline/*"],
      "@/lib/*":      ["src/lib/*"],
      "@/components/*": ["src/components/*"],
      "@/types/*":    ["src/types/*"],
      "@/store/*":    ["src/store/*"]
    }
  }
}
```
```typescript
// Import style — always use aliases
import { ComplianceBadge } from '@/features/compliance-officer/components/ComplianceBadge'
import { useAuth } from '@/lib/auth/useAuth'
import type { ProofCertificate } from '@/types/certificate'
// Never: import X from '../../../lib/auth/useAuth'
```

---

## 6. Environment Variables

| Variable | Purpose | Environment | Exposed to Frontend? |
|----------|---------|-------------|---------------------|
| `OPENROUTER_API_KEY` | LLM rule extraction | All | ❌ Never |
| `OPENROUTER_BASE_URL` | OpenRouter endpoint | All | ❌ Never |
| `LLM_DEFAULT_MODEL` | Primary model string | All | ❌ Never |
| `LLM_FALLBACK_MODEL` | Fallback model string | All | ❌ Never |
| `SUPABASE_URL` | DB + auth endpoint | All | ✅ Yes (anon key only) |
| `SUPABASE_ANON_KEY` | Frontend auth | All | ✅ Yes |
| `SUPABASE_SERVICE_KEY` | Backend admin ops | All | ❌ Never |
| `NEO4J_URI` | Knowledge graph connection | All | ❌ Never |
| `NEO4J_USERNAME` | Graph auth | All | ❌ Never |
| `NEO4J_PASSWORD` | Graph auth | All | ❌ Never |
| `MLFLOW_TRACKING_URI` | Experiment tracking | All | ❌ Never |
| `MLFLOW_EXPERIMENT_NAME` | Experiment grouping | All | ❌ Never |
| `PROOF_CERT_SECRET` | HMAC cert signing key | All | ❌ Never |
| `ENVIRONMENT` | dev / staging / production | All | ❌ Never |
| `LOG_LEVEL` | Logging verbosity | All | ❌ Never |
| `VITE_API_BASE_URL` | Frontend → FastAPI URL | Frontend | ✅ Yes (VITE_ prefix) |
| `VITE_SUPABASE_URL` | Frontend Supabase | Frontend | ✅ Yes (VITE_ prefix) |
| `VITE_SUPABASE_ANON_KEY` | Frontend auth | Frontend | ✅ Yes (VITE_ prefix) |

**Rules:**
- Any variable the React frontend needs must be prefixed `VITE_`
- `SUPABASE_SERVICE_KEY` never leaves the FastAPI backend process
- `PROOF_CERT_SECRET` rotates on every production deploy
- Adding a new env var → update `.env.example` in the same commit, no exceptions

---

## 7. Key Architectural Decisions

**1. Three-layer separation is enforced by import rules, not by convention**
Features cannot import from pipeline. Pipeline cannot import from features. This is enforced by a `ruff` import-order rule in CI — violations fail the build. The separation exists so the pipeline can be tested headlessly (no frontend) and the frontend can be developed against mock pipeline data.

**2. Colocated tests for pipeline stages, integration tests at top-level**
Each pipeline stage owns its tests (`pipeline/ci/tests/`). This keeps test code next to the logic it tests — a developer working on `symbolic_check.py` immediately sees `test_symbolic_check.py`. Top-level `tests/integration/` is reserved for full pipeline E2E tests that span multiple stages.

**3. Two React apps, one FastAPI backend, one Supabase auth**
The compliance officer and ML engineer interfaces share zero components — they are separate feature trees. They share one API client (`lib/api/client.ts`) and one auth system (Supabase role-based). Role is set at login: `compliance_officer` → routed to CO interface, `ml_engineer` → routed to MLE interface.

**4. WebSocket for pipeline events, REST for everything else**
Real-time pipeline status (gate passing, deployment progress) streams via WebSocket (`lib/ws/pipelineSocket.ts`). All other operations (fetching certificates, submitting regulations) use standard REST. This keeps the real-time surface small and auditable.

**5. Z3 client is a pure wrapper — no business logic**
`lib/z3_client.py` exposes exactly two methods: `prove(formula, constraints) → ProofResult` and `counterexample(formula, constraints) → Counterexample`. All Z3 business logic (which rules to check, how to encode model constraints) lives in `pipeline/ci/symbolic_check.py`. The client layer stays dumb.

**6. Proof certificate is immutable once written**
`cd/certificate.py` writes to Supabase once. There is no update path for a certificate. If a model is re-deployed (e.g. rolled back), a new certificate is generated for the rollback. The old certificate remains in the record. This is intentional — certificates are an audit trail, not a live status.

**7. GitHub Actions as orchestrator, not a custom scheduler**
CT is triggered by a GitHub Actions workflow dispatch event (fired by `ct/trigger.py` when regulation drift is detected). This keeps the pipeline observable — every CT run has a GitHub Actions run log, timing, and artifact. No hidden cron jobs or custom schedulers.

**8. Two Sources of Truth for Role Details**
To optimize read queries without sacrificing the security of Supabase JWTs, user roles will be stored in BOTH Supabase Auth metadata (for JWT resolution, enabling Row Level Security) AND the public `users` table (for efficient JOINs and dashboard listing).

---

*ARCHITECTURE.md is FINALIZED. File placement law. No exceptions without PRD + ARCH update.*
