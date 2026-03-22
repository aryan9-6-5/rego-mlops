# ISSUES.md — Bug Tracker & Known Gotchas
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: LIVE — append only, never delete entries
# ============================================================
# AI reads this BEFORE debugging anything.
# AI appends to this AFTER every session where a bug was found or solved.
# Format: one entry per issue, newest at top.
# ============================================================

## How to Use This File

**Before debugging:** Ctrl+F your error message or module name here first.
**After a session:** Log any bug found — even if fixed — so the next session doesn't repeat the investigation.
**Never delete entries.** Mark them `[RESOLVED]` instead.

---

## Issue Log

### Pre-Implementation — Known Design Gaps (from architecture audit)

---

**[DESIGN GAP — NOT YET HIT] ISSUE-005**
**Component:** `pipeline/ingestion/` — state machine
**Gap:** State machine in early docs had 4 states (`extracted → pending_approval → approved | rejected`). Correct state machine has 5 states: `extracted → z3_validated → pending_approval → approved | rejected` with a short-circuit `extracted → z3_rejected` path.
**Why it matters:** A Z3-rejected formula (malformed, not parseable) must never reach the human approval queue. The human only reviews structurally valid formulas.
**Resolution:** Updated in AIRULES.md Rule 5, PLAN.md Stage 2.1 migration, PLAN.md Stage 3.1 feature steps.
**Logged:** 2026-03-20 | By: framework audit

---

**[DESIGN GAP — NOT YET HIT] ISSUE-004**
**Component:** `ANTIGRAVITY_PROMPT.md`
**Gap:** Referenced `PRIVATE/ISSUES.md` but the file did not exist. Antigravity would fail on first session trying to read a missing file.
**Resolution:** Created this file. ISSUES.md now exists at `docs/ISSUES.md` (moves to `PRIVATE/ISSUES.md` on first Antigravity session).
**Logged:** 2026-03-20 | By: framework audit

---

**[DESIGN GAP — NOT YET HIT] ISSUE-003**
**Component:** `PLAN.md` Stage 6.5 — Demo Preparation
**Gap:** Railway free tier sleeps after 15 minutes of inactivity. The demo requires a timed 3-minute law-to-deployment walkthrough. A cold start (~30s) would break the opening of the demo.
**Resolution:** Add to PLAN.md Stage 6.5 checklist: "Send a warm-up request to the Railway URL 5 minutes before demo starts (`curl https://[app].railway.app/health`) to prevent cold start during live demo."
**Logged:** 2026-03-20 | By: framework audit

---

**[DESIGN GAP — NOT YET HIT] ISSUE-002**
**Component:** `TECH.md` — pinned frontend devDependencies
**Gap:** `TESTING.md` specifies Playwright for E2E tests but `@playwright/test` is missing from the `package.json` devDependencies in TECH.md Section 5.
**Resolution:** Add `"@playwright/test": "^1.44.0"` to TECH.md devDependencies before Stage 5.
**Logged:** 2026-03-20 | By: framework audit

---

**[DESIGN GAP — NOT YET HIT] ISSUE-001**
**Component:** `PLAN.md` Stage 2.1 + `TECH.md` Section 4
**Gap:** PLAN.md Stage 2.1 creates a `users` table with a `role` column. Supabase Auth also stores role in JWT metadata. Two sources of truth for role — they can drift.
**Resolution:** Store role in BOTH: Supabase Auth metadata (for JWT — fast auth checks) AND `users` table (for query joins and audit). On role change, update both atomically. Document this dual-write in ARCHITECTURE.md Section 7 as Decision 8 before Stage 2.
**Logged:** 2026-03-20 | By: framework audit

---

## Entry Template
*(copy this when logging a new issue)*

```
**[OPEN | RESOLVED] ISSUE-XXX**
**Component:** [file or module where the bug lives]
**Error:** [exact error message or description]
**Root cause:** [why it happened]
**Fix:** [what was changed]
**Regression test:** [test file that now covers this — or 'none yet']
**Logged:** [YYYY-MM-DD] | By: [AI — auto | Me — manual]
```

---

*ISSUES.md is append-only. Never delete. Mark resolved with [RESOLVED].*
*AI appends here automatically at session end when bugs are found or resolved.*
