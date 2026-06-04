# Rego MLOps: Continuous Regulatory Compliance Reasoning

> **"Every other MLOps platform retrains when data changes. Rego retrains when the LAW changes."**

Rego is a next-generation MLOps and RegTech platform that integrates regulatory compliance as a first-class, automated gate in the Machine Learning lifecycle. Instead of treating compliance as a manual, post-hoc audit process, Rego uses **neuro-symbolic AI**—combining Large Language Models (LLMs) for legal text translation with the **Z3 SMT Solver** for formal mathematical verification—to enforce regulatory compliance before models ever reach production.

---

## 🚀 The Core Innovation: Why Rego is Unprecedented

Traditional financial institutions spend millions of dollars and months of manual engineering effort trying to align their credit scoring and decision-making models with changing guidelines. Rego automates this entire loop, making legal change the primary driver of Continuous Training (CT).

| What everyone else builds | What Rego builds |
|:---|:---|
| **CT triggered by data drift** | **CT triggered by regulatory drift** (law changes) |
| **Compliance as post-deployment audit** | **Compliance as deployment gate** (automated block) |
| **Engineers interpret laws manually** | **LLM drafts candidate logic, Z3 validates structure, human approves semantic intent** |
| **Audit = 400-page PDF report** | **Audit = 10-second machine-verifiable proof certificate** |
| **Model versions tracked** | **Law versions + Model versions tracked together in a lineage graph** |
| **Compliance is a feature** | **Compliance is the pipeline** |
| **Compliance team is external** | **Compliance officer is a pipeline actor** |

---

## 🛠️ The Tech Stack

- **Reasoning Core**: Microsoft Research's **Z3 SMT Solver** (pinned at `4.12.6.0`)
- **LLM Layer**: **OpenRouter API** (Claude 3.5 Sonnet with GPT-4o fallback)
- **Backend API**: **FastAPI** (Python 3.11)
- **Knowledge Graph**: **Neo4j Aura** (Regulatory rule version lineage & model mapping)
- **Database & Auth**: **Supabase** (Postgres data store, real-time events, and RBAC auth)
- **Model Registry & Tracking**: **MLflow** & **DVC**
- **Frontend**: **React 18** + **TypeScript** + **Vite** + **Vanilla CSS**
- **Infrastructure**: **Docker & Docker Compose** for local dev, **Railway** for production

---

## 📐 Architecture Diagram

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

## ✈️ The Z3 Story: Aerospace Verification for Finance

To guarantee compliance, we cannot rely on probabilistic models like LLMs to make the final determination. LLMs can hallucinate, drift, or make logical errors. 

Rego solves this by leveraging **Satisfiability Modulo Theories (SMT)** via Microsoft’s Z3 solver. This is the exact same class of formal verification used to prove the correctness of safety-critical systems like:
- **Boeing 787 flight control software**
- **Intel CPU logic circuits**
- **NASA space shuttle control models**

When a new regulation is ingested, the system represents it as a Z3 logical formula, and models express their decision weights as mathematical constraints. Z3 then attempts to find a scenario where the model violates the rule:
- **UNSATISFIABLE (UNSAT)**: The solver proves it is mathematically impossible to violate the regulation under the model's constraints. The model is **compliant**.
- **SATISFIABLE (SAT)**: The solver finds a model assignment (a **counterexample**) showing exactly how the model violates the regulation. The model is **non-compliant**, and the counterexample is translated into plain language.

---

## 📋 Core Workflows & How They Work

### 1. Ingestion: How to Add an RBI Rule
1. A **Compliance Officer (CO)** uploads or pastes a raw legal circular (e.g., India's RBI Master Direction on Digital Lending, 2022).
2. The **LLM Ingestion Engine** (`src/pipeline/ingestion/extractor.py`) parses the text and drafts a candidate Z3 formula.
3. The **Ingestion Validator** (`src/pipeline/ingestion/validator.py`) passes the formula to Z3 to ensure it is structurally sound, valid, and free of contradictions.
4. A three-signal **Confidence Score** is calculated (completeness, Z3-validity, specificity).
5. The CO reviews the raw text side-by-side with the translated formula and submits **Human Approval** (a two-click flow).
6. Approved rules are versioned and stored in the **Neo4j Knowledge Graph** as `(:Regulation)` nodes.

### 2. Verification: How to Submit a Model
1. The **ML Engineer (MLE)** registers a model artifact or submits a new version.
2. The **CI compliance-aware gate** is triggered (`src/pipeline/ci/gate_runner.py`), running four sequential stages:
   * **Symbolic Check**: Z3 checks the model's feature weights against all active rules stored in Neo4j.
   * **RegAttack**: Adversarial regulatory tests attempt to force the model into edge-case violations.
   * **Fairness Check**: Demographic parity checks via Evidently AI.
   * **Regression Check**: Evaluates performance regression to prevent F1-score drops.
3. If any gate fails, the pipeline halts immediately, generating a plain-English explanation of the exact rule violated and the Z3 counterexample values.

### 3. Certification: How Proof Certificates Work
1. When all CI gates pass, the deployment gate is unlocked.
2. The CD system (`src/pipeline/cd/certificate.py`) collects the Z3 proof hashes, model metadata, and active regulation versions.
3. An **immutable Proof Certificate** is generated, signed using a secure HMAC key, and stored in Supabase.
4. Auditors can verify the integrity of the proof certificate in under 10 seconds via the verification endpoint without exposing underlying model internals.

---

## ⚙️ Getting Started

### Prerequisites
- **Python**: `3.11.x`
- **Node.js**: `18.x+` (with npm)
- **Docker**: For running database and graph services locally
- **Poetry**: Python dependency management

### Local Setup

1. **Clone the Repository & Environment Configuration**
   ```bash
   git clone https://github.com/aryan9-6-5/rego-mlops.git
   cd rego-mlops
   cp .env.example .env
   # Fill in the required environment variables in .env (OpenRouter API, Supabase, Neo4j, etc.)
   ```

2. **Backend Setup**
   ```bash
   # Install backend dependencies
   poetry install
   
   # Verify Z3 installation works
   poetry run python scripts/verify_z3_install.py
   
   # Start local services (Neo4j, etc.)
   docker-compose up -d
   
   # Run local database seed script
   poetry run python scripts/seed_rbi_rules.py
   
   # Run the FastAPI API server
   poetry run uvicorn src.api.main:app --reload --port 8000
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev  # Vite launches the UI at http://localhost:5173
   ```

4. **Run Proof of Concept (PoC)**
   Execute the standalone Stage 0 script that verifies Z3 and LLM extraction end-to-end:
   ```bash
   poetry run python scripts/poc_pipeline.py
   ```

---

## 🤖 GitHub Actions Workflows

We use three GitHub Actions workflows under `.github/workflows/` to orchestrate our pipeline:

1. **CI (`ci.yml`)**: Triggered on every `push` and `pull_request` to the `main` branch.
   * Installs Python/Node environments.
   * Runs Python linting (`ruff`) and strict typing checks (`mypy`) in `/src`.
   * Runs pytest for backend compliance and solver tests.
   * Runs ESLint and Vitest suite in `/frontend`.
2. **CD (`cd.yml`)**: Triggered automatically after a successful `CI` workflow run on the `main` branch.
   * Deploys the built application to production (Railway stub).
3. **CT (Continuous Training) (`ct.yml`)**: Manually triggered or triggered on regulation change events via `workflow_dispatch`.
   * Accepts a `regulation_version` input.
   * Retrains the model (classical XGBoost utilizing compliance constraint loss terms) on a Kaggle P100 GPU and registers the new artifact in MLflow.

---

## 📁 Project Structure

```text
rego/
├── .github/workflows/      # CI/CD/CT automation pipelines
├── docs/                   # Internal project requirements and rule sheets
├── src/                    # Backend source code (FastAPI + Z3/Neo4j/Supabase logic)
│   ├── api/                # FastAPI app definitions, dependencies, schemas & routers
│   ├── features/           # UI-associated endpoint logic
│   ├── lib/                # Infrastructure clients (Z3, OpenRouter, Neo4j, Supabase, MLflow)
│   └── pipeline/           # Core compliance logic (ingestion, ci, ct, cd)
├── frontend/               # React + TypeScript Vite frontend
│   └── src/
│       ├── features/       # Role-based dashboard interfaces (CO layout & MLE layout)
│       ├── components/     # Shared UI components and primitives
│       ├── lib/            # API clients, WS event handlers, and auth hooks
│       └── store/          # Zustand state stores
├── scripts/                # Utility scripts (seeding rules, verifying install, PoC runner)
├── notebooks/              # CT retraining notebooks running on Kaggle GPU
├── tests/                  # Integration and E2E test files
├── Dockerfile              # Multi-stage Docker builder for FastAPI
├── docker-compose.yml      # Multi-container local service configuration
└── pyproject.toml          # Poetry dependencies and lint configuration
```

---

## 📝 License

This project is licensed under the MIT License.
