# STATE.md — Live Project State
# Project Rego — Continuous Regulatory Compliance Reasoning
# ============================================================
# THIS FILE IS THE HEARTBEAT OF THE PROJECT.
# Read at the START of every AI session — before anything else.
# Updated at the END of every AI session — no exceptions.
# If this file is stale, the whole system is working blind.
# ============================================================

# ============================================================
# OWNERSHIP RULES — read before editing this file
# ============================================================
#
# WHO UPDATES THIS FILE:
#   AI (automatic) → after every completed task, every session
#   You (manual)   → only when resuming after 24h+ break,
#                    or when you did something outside an AI session
#
# WHEN IT'S WRONG:
#   If STATE.md and reality disagree → STATE.md is wrong.
#   Fix it before doing anything else. Never work from stale state.
#
# STALENESS RULE:
#   If Last Updated is more than 24h ago — treat as potentially stale.
#   AI asks: "Is [current step] still accurate, or has something changed?"
#   before proceeding.
#
# GRANULARITY RULE (important for this project):
#   Update after EVERY sub-step completion, not just stage completion.
#   PLAN.md has ~120 checklist items. STATE.md tracks which one is active NOW.
#   "Stage 1 in progress" is not specific enough.
#   "Stage 1.2 — ruff configured, mypy in progress" is correct.
# ============================================================

# ============================================================
# LIVE STATE — AI updates this block after every task
# ============================================================

## 🕒 Status Snapshot
- **Current Stage**: Stage 1.3 — CI Skeleton
- **Last Updated**: 2026-03-22
- **Health**: 🟢 Healthy (All checks passing)

---

## Last Completed

> Stage 1.1 + 1.2 — Repository, Dependencies, Linting, and Typing Complete.
> All environments (Python, NPM) initialized, Ruff/MyPy/ESLint configured and passing.
> local `verify.bat` confirmed green.

---

## Current Step (in detail)

> Stage 1.3 — CI Skeleton.
> Goal: Create GitHub Actions workflows for continuous validation.


---

## Next Action

> **Exact next action (Stage 1.3):**
> 1. Draft `.github/workflows/ci.yml`
> 2. Prepare CD and CT skeletons.

---

## Blockers

> None.

---

## Open Decisions

> None. All architecture, tech stack, and design decisions are finalized in docs.
> If a decision comes up during implementation — check the relevant doc first.
> If not covered — add to Open Decisions here before proceeding.

---

## Recent Changes (last 3 sessions)

| Date | What changed | Files affected |
|------|-------------|----------------|
| 2026-03-22 | Git Reset: Hard reset repository to fix tracking of ignored files | .git/, .gitignore |
| 2026-03-22 | Stage 1.1 + 1.2 Complete: Repo setup & Linting | All files, docs/STATE.md, docs/PLAN.md |
| 2026-03-22 | Stage 0 Complete: Implemented PoC pipeline | scripts/poc_pipeline.py, docs/STATE.md, docs/PLAN.md |
| 2026-03-20 | All 10 framework docs finalized | docs/PRD.md, TECH.md, ARCHITECTURE.md, DESIGN.md, AIRULES.md, CONSTRAINTS.md, TESTING.md, PLAN.md, SKILLS.md, LLM_INSTRUCTIONS.md |

---

## Stage Progress Tracker
*(AI updates checkboxes as each sub-stage completes)*

### Stage 0 — Proof of Concept ← COMPLETE
- [x] 0.1 Minimal Z3 Compliance Check (hardcoded RBI rule + Z3)
- [x] 0.2 LLM Rule Extraction (live OpenRouter call)
- [x] 0.3 Confidence Score (3-signal calculation)
- [x] 0.4 Full PoC Run end-to-end (< 60 seconds, prints full demo output)

| Stage | Status | Progress |
| :--- | :--- | :--- |
| **Stage 0: Proof of Concept** | ✅ Complete | 100% (Local Z3 + LLM verified) |
| **Stage 1: Basic Scaffolding** | 🏗️ In Progress | 50% (Repo, Deps, Linting complete) |
| **Stage 1.1: Repository & Dependency Setup**| ✅ Complete | 100% (Poetry, NPM setup) |
| **Stage 1.2: Linting & Type Checking** | ✅ Complete | 100% (Ruff, MyPy, ESLint passing) |
| **Stage 1.3: CI Skeleton** | 📅 Next | 0% (Pending Start) |
- [ ] 1.4 Docker Local Dev

### Stage 2 — Core Infrastructure
- [ ] 2.1 Supabase — Database Schema
- [ ] 2.2 Neo4j — Knowledge Graph Model
- [ ] 2.3 FastAPI Skeleton
- [ ] 2.4 Supabase Auth + Role-Based Routing
- [ ] 2.5 React Scaffold — Both Interfaces

### Stage 3 — Pipeline Features
- [ ] 3.1 Regulatory Ingestion Engine
- [ ] 3.2 Regulatory Version Control & Lineage Graph
- [ ] 3.3 Compliance-Aware CI Gates
- [ ] 3.4 Regulatory-Triggered CT
- [ ] 3.5 Compliance-Gated CD
- [ ] 3.6 Proof Certificate Generation
- [ ] 3.7 HCI Dashboard (full implementation)

### Stage 4 — Security Hardening
- [ ] 4.1 Authentication & Authorization Audit
- [ ] 4.2 Certificate & Cryptographic Security
- [ ] 4.3 Input Sanitization
- [ ] 4.4 Data Privacy (PII)
- [ ] 4.5 Dependency Security
- [ ] 4.6 Rate Limiting

### Stage 5 — Testing
- [ ] 5.1 Unit Test Coverage
- [ ] 5.2 Integration Tests
- [ ] 5.3 E2E Tests
- [ ] 5.4 Manual QA Pass

### Stage 6 — Polish & Deploy
- [ ] 6.1 Performance
- [ ] 6.2 Accessibility (CO Interface)
- [ ] 6.3 README
- [ ] 6.4 Railway Deploy
- [ ] 6.5 Demo Preparation

---

## Environment Status

| Environment | Status | Last deployed | Notes |
|-------------|--------|---------------|-------|
| Local dev | Not set up | — | Stage 1.4 sets up Docker compose |
| Staging | Not set up | — | Stage 6.4 |
| Production | Not deployed | — | Stage 6.4 |

---

## Quick Reference

```
Repo:       https://github.com/aryan9-6-5/rego-mlops.git
Local API:  http://localhost:8000
Local UI:   http://localhost:5173
Swagger:    http://localhost:8000/docs
Neo4j:      http://localhost:7474 (local Docker)
Supabase:   https://[project-id].supabase.co        ← update when created
Railway:    https://[app-name].railway.app           ← update at Stage 6.4
Branch:     main

Key files:
  Compliance core:   src/pipeline/ci/symbolic_check.py
  Z3 client:         src/lib/z3_client.py
  Certificate logic: src/pipeline/cd/certificate.py
  CO interface:      frontend/src/features/compliance-officer/
  MLE interface:     frontend/src/features/ml-engineer/
  RBI seed script:   scripts/seed_rbi_rules.py
```

---

# ============================================================
# HOW AI USES THIS FILE — session protocol
# ============================================================
#
# SESSION START (every single session, no exceptions):
#   1. Read STATE.md — this file, completely
#   2. Check Last Updated timestamp
#      — If < 24h ago: proceed normally
#      — If > 24h ago: say "STATE.md was last updated [X] ago.
#        Is [current sub-stage + step] still accurate, or has
#        something changed since then?"
#   3. State current position out loud:
#      "STATE.md: Stage [X], Sub-stage [Y], step [Z].
#       Next action: [exact next action from this file].
#       Has anything changed since [last updated]?"
#   4. Wait for confirmation or correction before writing code.
#
# DURING SESSION (after completing each checklist item):
#   Update immediately:
#   ✏️  Current Step → the next unchecked item
#   ✏️  Next Action → specific enough for a cold AI to execute
#   ✏️  Stage Progress Tracker → check the completed box
#   ✏️  Last Completed → one sentence summary
#
# SESSION END (before every session close, no exceptions):
#   Final update to:
#   ✏️  Last Updated → current timestamp
#   ✏️  Updated By → "AI — auto"
#   ✏️  Last Completed → what was finished this session
#   ✏️  Current Step → where things stand right now
#   ✏️  Next Action → the single specific next thing
#   ✏️  Blockers → any new blockers discovered
#   ✏️  Recent Changes → add one row to the table
#   ✏️  Environment Status → update if anything deployed/broken
#   ✏️  Stage Progress Tracker → mark completed sub-stages ✅
#
#   Then post SESSION SUMMARY in chat before closing:
#
#   "✅ Done: [list of completed items this session]
#    📍 Now at: Stage [X], Sub-stage [Y] — [name]
#    ➡️  Next: [exact next action — specific file, specific command]
#    ⚠️  Open: [blockers or open decisions, or 'None']
#    🕐 STATE.md updated [timestamp]"
#
# GRANULARITY REMINDER:
#   This project has ~120 checklist items across 20 sub-stages.
#   Update STATE.md after every sub-stage, not just every stage.
#   "Stage 3 in progress" tells the next AI nothing useful.
#   "Stage 3.3 — symbolic_check.py done, reg_attack.py next" is correct.
#
# IF BLOCKED:
#   Write the blocker in the Blockers section immediately.
#   Do not leave Blockers empty if something is actually blocking you.
#   Format: "[what is blocked] — [why] — [what is needed to unblock]"
#   e.g. "3.3 symbolic_check.py — Z3 formula encoding for
#         RBI §4.1.c unclear — need to read RBI circular text first"
# ============================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STATE.md is now your project's live pulse.

HOW IT STAYS CURRENT:
  After every AI task → AI updates it automatically
  After a 24h+ break → you update it manually before starting
  When reality changes → fix it immediately, before anything else

ONE RULE: If this file says one thing and reality says
another — reality wins. Update this file first.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
