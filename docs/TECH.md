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
| **API Backend** | FastAPI | `0.111.x` | Async, auto-generates OpenAPI docs (Swagger), Python-native |
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

### HCI Dashboard
```
Backend:  FastAPI (REST + WebSocket for real-time status)
Frontend: React 18 (two interfaces: compliance officer + ML engineer)
Auth:     Supabase Auth (role-based: compliance_officer | ml_engineer | cto)
DB:       Supabase PostgreSQL (pipeline events, certificate records, user sessions)
Graph:    Neo4j Aura (lineage queries — "which law was this model compliant with?")
```

---

## 5. Pinned Versions (Lockfile)

These are the approved versions. Do not upgrade without updating this file and re-running full CI.

```toml
# pyproject.toml — key dependencies
[tool.poetry.dependencies]
python = "^3.11"
z3-solver = "4.12.6.0"          # PINNED — never auto-upgrade
fastapi = "^0.111.0"
uvicorn = "^0.29.0"
torch = "^2.2.0"
transformers = "^4.40.0"
mlflow = "^2.12.0"
dvc = "^3.49.0"
evidently = "^0.4.22"
neo4j = "^5.19.0"               # Neo4j Python driver
supabase = "^2.4.0"
openai = "^1.25.0"              # OpenRouter uses OpenAI-compatible SDK
kaggle = "^1.6.0"               # Kaggle API — CT retraining trigger
httpx = "^0.27.0"
pydantic = "^2.7.0"
python-dotenv = "^1.0.0"
poetry-dynamic-versioning = "^1.3.0"

[tool.poetry.dev-dependencies]
pytest = "^8.2.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^5.0.0"
black = "^24.4.0"
ruff = "^0.4.0"
mypy = "^1.10.0"
```

```json
// package.json — frontend key dependencies
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "axios": "^1.6.0",
    "react-dropzone": "^14.2.0",
    "@tanstack/react-query": "^5.36.0",
    "zustand": "^4.5.0",
    "recharts": "^2.12.0",
    "tailwindcss": "^3.4.0"
  },
  "devDependencies": {
    "vite": "^5.2.0",
    "typescript": "^5.4.0",
    "@types/react": "^18.3.0",
    "vitest": "^1.6.0",
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
