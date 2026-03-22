# PRD.md — Project Rego
# Continuous Regulatory Compliance Reasoning Platform
# Version: 1.0 | Status: FINALIZED
# ============================================================

## 1. Product Overview

**Name:** Rego
**Tagline:** "Every other MLOps platform retrains when data changes. Rego retrains when the LAW changes."
**One-liner:** A FinTech MLOps platform where legal compliance is a first-class citizen of the deployment pipeline — not an afterthought audit.
**Problem:** Laws governing financial ML models change constantly across 190+ jurisdictions. Banks have no automated way to know when their deployed models become non-compliant. The current process — lawyers → emails → engineers → 8 months → $2–4M — is broken. Models run illegally without anyone knowing.
**Category:** MLOps Infrastructure / RegTech / Neuro-Symbolic AI

---

## 2. What This App IS ✅

Rego is an MLOps pipeline platform that treats **regulatory law change** as the primary trigger for Continuous Training (CT), replacing the industry-standard data drift trigger.

**The core innovation:** Given a set of regulatory rules R and a model M, Rego continuously and provably answers — "Does M satisfy R? And when R changes, how must M change to remain compliant?" — using neuro-symbolic AI baked directly into CI/CD/CT.

### Primary Users

| User | Role | Core Need |
|------|------|-----------|
| Compliance Officer | Non-technical, law expert | Paste regulatory text → see compliance status → approve/reject, zero coding |
| ML Engineer / Quant | Technical, hates compliance paperwork | Automated compliance in pipeline, no manual legal interpretation |
| Bank CTO / Risk Officer | Executive oversight | Proof certificates for regulators, zero model risk surprises |

### Core Features (v1)

**Feature 1 — Regulatory Ingestion Engine**
- Compliance officer pastes or uploads regulatory text (plain language law)
- LLM converts natural language → *candidate* formal logic rule (a draft, not a final rule)
- Z3 validates the candidate formula for well-formedness and internal consistency — malformed or contradictory logic is rejected before it ever reaches a human
- Compliance officer reviews: source regulation text on the left, candidate logic translation on the right — approves or rejects with explicit confirmation (two deliberate actions)
- Approved rule gets versioned and stored in the knowledge graph
- Every rule has a unique ID, version timestamp, jurisdiction tag, and source citation

**The LLM ↔ Z3 trust model — explicitly resolved:**
LLM is a *drafting tool*, not a reasoning engine. Z3 is the reasoning engine. Humans are the semantic validators. This mirrors how law firms work: a junior associate drafts a clause (LLM), a senior partner checks it for legal consistency (Z3 well-formedness), and the client approves the intent (human). The LLM is not trusted to produce correct logic — it is trusted to produce a *plausible candidate* that a human and Z3 together validate. "Garbage in → perfectly verified garbage out" is prevented by the human approval gate: the human confirms the formula captures the regulatory intent before Z3 ever uses it as a compliance standard.

**Feature 2 — Regulatory Version Control & Lineage Graph**
- Law versions and model versions tracked together in the same lineage graph
- Every deployment answers: "Which exact version of which regulation was this model compliant with?"
- Lineage is queryable — full audit trail from any model version back to the specific regulation text
- This is what makes the proof certificate legally meaningful

**Feature 3 — Compliance-Gated CD (Continuous Deployment)**
- Model is blocked from reaching production if it fails compliance gates
- The block is at deployment, not at commit — engineers can still commit and iterate freely
- Zero-downtime logic hot-swap: compliant model replaces previous version in under 3 minutes
- Canary deployment with compliance shadow testing before full rollout
- No deployment proceeds without a passing compliance score

**Feature 4 — Compliance-Aware CI (Continuous Integration)**
- Every model submission triggers symbolic consistency checks against ALL active regulatory rules
- Adversarial regulatory attack tests (RegAttack) — probing model with edge-case regulatory scenarios
- Fairness checks baked into CI gates
- Statistical performance regression tests
- All gates must pass, or pipeline halts with a precise explanation of which rule was violated and why

**Feature 5 — Regulatory-Triggered CT (Continuous Training)**
- New or amended regulation detected → automatic retraining triggered
- CT is triggered by law drift, not data drift
- Model retrained with new compliance constraints baked into the training objective
- This is the core innovation no other MLOps platform has built

**Feature 6 — Proof Certificate Generation (Per Deployment)**
- Every successful deployment generates one machine-verifiable proof certificate
- Certificate = model version + regulation version(s) + compliance score + symbolic proof hash
- Auditor can verify compliance in under 10 seconds
- Replaces 400-page PDF audit reports
- Certificate is NOT generated per-decision (that would be millions of PDFs — operationally impossible)

**Feature 7 — HCI Dashboard (Two-Interface System)**
- Compliance Officer Interface: drag-and-drop regulatory text, live compliance status, plain-English explanations, approve/reject controls, no code required
- ML Engineer Interface: pipeline status, rule violations with exact technical detail, model diff viewer, deployment controls
- Same underlying system — two completely different cognitive interfaces
- Principles: Visibility, Control, Feedback, Error Prevention, Accessibility (see Section 7)

---

## 3. What This App is NOT ⛔

These are hard exclusions. Any AI tool working on this project must never implement these.

| What it is NOT | Why it matters |
|----------------|----------------|
| NOT a fraud detection system | Different ML problem entirely — do not conflate |
| NOT a credit scoring engine | Rego monitors compliance OF models, not runs models for decisions |
| NOT a per-decision PDF generator | Proof certificates are per-deployment, not per-inference |
| NOT a lawyer replacement | LLM converts law to logic, human always approves. AI suggests, human decides |
| NOT a compliance chatbot | Not conversational — it's a pipeline infrastructure tool |
| NOT blocking commits | CI/CD blocks DEPLOYMENT, not the commit. Engineers iterate freely |
| NOT a multi-jurisdiction system in v1 | MVP targets one jurisdiction only (India RBI + RBI Fair Practices Code or India RBI) |
| NOT real-time per-inference compliance checking | Compliance validated at deployment time, not inference time |
| NOT a general-purpose MLOps platform | Purpose-built for regulatory compliance — not a Kubeflow replacement |

---

## 4. User Stories

### Compliance Officer
- As a compliance officer, I can paste new regulatory text and get a logic-rule translation in under 2 minutes, so I never have to write code to enforce compliance.
- As a compliance officer, I can approve or reject any rule before it enters the pipeline, so humans always have final say over what the model must comply with.
- As a compliance officer, I can see the live compliance status of the currently deployed model in plain English at any time, without asking an engineer.
- As a compliance officer, I can generate a proof certificate for any deployed model version and send it to a regulator in under 10 seconds.

### ML Engineer
- As an ML engineer, I can push a model update and know exactly which regulatory rule it violates and why — without reading a single legal document.
- As an ML engineer, I can see a visual diff between two model versions showing exactly what compliance posture changed.
- As an ML engineer, I never have to manually translate laws into code — the system handles it and flags for human approval.

### Bank CTO / Risk Officer
- As a CTO, I can prove to regulators that every deployed model is compliant with a specific named version of a specific regulation.
- As a CTO, I am notified within minutes when a new regulation is detected that could affect deployed models.
- As a CTO, no model can reach production without passing compliance gates — the system enforces this structurally, not by policy.

---

## 5. Success Metrics

| Metric | Target |
|--------|--------|
| Time from law change to compliant deployment | Under 3 minutes |
| Compliance officer onboarding time | Under 10 minutes, zero coding |
| False compliance rate | 0% — model never deploys if non-compliant |
| Proof certificate generation time | Under 10 seconds |
| Pipeline explainability | Every violation traced to exact rule ID + plain English reason |
| Reviewer / demo reaction | Jaw-drop moment on first walkthrough |

---

## 6. Constraints

| Constraint | Detail |
|------------|--------|
| Budget | $0 — free tier infrastructure only for MVP |
| Jurisdiction scope | MVP: 1 jurisdiction (India RBI or India RBI — to be decided in TECH.md) |
| Model type scope | MVP: loan approval model only |
| Deployment target | Railway / Render / HuggingFace Spaces (free tier) |
| Compliance gate | Hard gate — no override, no bypass in v1 |
| LLM usage | LLM used only for rule extraction (offline/batch) — not in inference path |
| Human approval | Every LLM-generated rule must be human-approved before activation |
| Legal disclaimer | Rego provides compliance tooling, not legal advice. Output is not a legal opinion |

---

## 7. HCI Principles (Non-Negotiable)

These are structural product requirements, not design preferences.

| Principle | Implementation |
|-----------|---------------|
| **Visibility** | Compliance status always visible in plain English. No hidden states |
| **Control** | Humans approve every logic translation. AI suggests, human decides — always |
| **Feedback** | Every pipeline stage produces immediate, clear output: what passed, what failed, and exactly why |
| **Error Prevention** | Model structurally cannot deploy without compliance gates — not enforced by policy, enforced by architecture |
| **Accessibility** | Two separate interfaces for technical and non-technical users. Neither interface requires knowledge of the other domain |

---

## 8. CI/CD/CT Architecture Flow

```
[New Regulation Drops]
        ↓
[Regulatory Ingestion Engine]
  LLM reads law → generates CANDIDATE formal logic rule (draft)
  Z3 validates: is this formula well-formed and consistent?
    → Malformed: rejected immediately, error returned to CO
    → Well-formed: shown to compliance officer for review
  Compliance officer approves the SEMANTIC INTENT (two deliberate clicks)
  Only after both Z3 structural check + human semantic approval does rule activate
        ↓
[Knowledge Graph Updated]
  New rule versioned (rule_id, version, jurisdiction, source_citation)
  Lineage graph updated: regulation_version ←→ affected_model_versions
        ↓
[CT TRIGGERED — by LAW drift, not data drift]
  Model retrained with new compliance constraints in objective
        ↓
[CI — Continuous Integration Gates]
  ✓ Symbolic consistency checks vs ALL active rules
  ✓ RegAttack adversarial regulatory tests
  ✓ Fairness checks
  ✓ Statistical regression tests
  ALL must pass → else pipeline halts with exact violation report
        ↓
[CD — Continuous Deployment]
  Canary release + compliance shadow testing
  Proof certificate generated (model_version + regulation_version + proof_hash)
  Zero-downtime hot-swap
  Time from law change to compliant production: < 3 minutes
        ↓
[PRODUCTION MODEL]
  Mathematically proven compliant
  Certificate queryable by auditors in < 10 seconds
```

---

## 9. What Makes Rego Unprecedented

| What everyone else builds | What Rego builds |
|--------------------------|-----------------|
| CT triggered by data drift | CT triggered by regulatory drift |
| Compliance as post-deployment audit | Compliance as deployment gate |
| Engineers interpret laws manually | LLM drafts candidate logic, Z3 validates structure, human approves semantic intent |
| Audit = 400-page PDF | Audit = 10-second machine-verifiable proof |
| Model versions tracked | Law versions + Model versions tracked together in lineage graph |
| Compliance is a feature | Compliance is the pipeline |
| Compliance team is external to pipeline | Compliance officer IS a pipeline actor |

---

## 10. MVP Scope

### Phase 1 — Core Pipeline
- One jurisdiction (India RBI — Master Directions on Digital Lending 2022 + Fair Practices Code)
- One model type: loan approval
- CI pipeline with symbolic rule checking
- Manual regulatory ingestion (paste text → human-approved rules)
- Deployment gate (model blocked if non-compliant)

### Phase 2 — Automation
- LLM-assisted rule extraction from raw regulatory documents
- CT triggered automatically on regulatory update detection
- Proof certificate generation

### Phase 3 — HCI Dashboard
- Compliance officer interface (non-technical)
- ML engineer interface (technical)
- Live compliance monitoring
- Visual model diff on version change

---

## 11. Full Project Scope — Everything Gets Built

This is the complete project. There is no v1/v2 split. All features below are in scope and will be implemented:

| Feature | Status |
|---------|--------|
| RBI India jurisdiction (Master Directions 2022 + Fair Practices Code) | In scope |
| Loan approval model (classical ML — XGBoost) | In scope |
| Regulatory ingestion engine (LLM → Z3 → human approval) | In scope |
| Regulatory version control + lineage graph | In scope |
| Compliance-aware CI gates (Z3 + RegAttack + fairness + regression) | In scope |
| Regulatory-triggered CT (law drift → retrain on Kaggle GPU) | In scope |
| Compliance-gated CD (zero-downtime Railway deploy) | In scope |
| Proof certificate generation + verification | In scope |
| HCI Dashboard — Compliance Officer interface | In scope |
| HCI Dashboard — ML Engineer interface | In scope |
| Real-time pipeline status (WebSocket) | In scope |
| Visual model diff between versions | In scope |
| Multi-jurisdiction support (190+ jurisdictions) | Out of scope — genuine infrastructure problem requiring legal partnerships |
| External SaaS API for other companies | Out of scope — requires enterprise sales, legal, multi-tenancy |
| Per-inference compliance checking | Out of scope — architecturally wrong approach (see PRD Section 3) |
| SOC 2 / ISO 27001 certification | Out of scope — requires paid auditors |
| Enterprise SSO / SAML | Out of scope — beyond portfolio project scope |

---

*PRD.md is FINALIZED. Do not modify without updating version number and notifying all AI tools via STATE.md.*

