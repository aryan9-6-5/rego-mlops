# SKILLS.md — AI Workflow Framework
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: FINALIZED
# ============================================================
# The operating manual for how AI tools work on this project.
# The most valuable section is Section 5 — Standard Prompts.
# Copy-paste those templates instead of re-explaining context
# every session.
# ============================================================

## 1. AI Tool Roster

| Tool | Role | Use for | Never use for |
|------|------|---------|---------------|
| **Claude (claude.ai / Claude Code)** | Primary builder | All code generation, architecture decisions, debugging, doc updates, Z3 formula design, prompt engineering | Final security audit (use your own judgment there) |
| **Claude Code (terminal)** | Agentic implementation | Multi-file edits, running tests, refactoring across the codebase, scaffold generation | Quick questions — use claude.ai chat instead |
| **Cursor / VS Code Copilot** | IDE autocomplete | Line completions, boilerplate fill, quick syntax | Architectural decisions, anything touching compliance logic |
| **ChatGPT / Gemini** | Concept questions | Understanding Z3 concepts, RBI regulation interpretation, quick definitions | Writing any Rego code — context is missing |
| **DeepSeek (code review)** | Second-opinion review | Code review of compliance-critical files before merge | First-pass generation — Claude does generation, DeepSeek reviews |

**Tool handoff rule:** Claude generates → DeepSeek reviews compliance-critical files (`symbolic_check.py`, `certificate.py`, `approver.py`) → you approve → merge.

---

## 2. Problem-Solving Framework

Before writing a single line of code, run this sequence every time:

```
STEP 1 — ORIENT (read before touching anything)
  □ Read STATE.md — what stage, what step, what's next
  □ Read ISSUES.md — has this class of problem been hit before?
  □ Check git log --oneline -10 — what changed recently?

STEP 2 — LOCATE (find the right files)
  □ Open ARCHITECTURE.md Section 2 (File Placement Rules)
  □ Identify which layer this work belongs to:
      /features/ → UI only
      /pipeline/ → CI/CD/CT logic
      /lib/      → shared clients
  □ Confirm no existing file already does this

STEP 3 — PLAN (write the plan before writing code)
  □ State the task in one sentence
  □ List files to create or modify (max 3-5 per session)
  □ Check CONSTRAINTS.md — does this add a new service/package?
  □ Check AIRULES.md — any rule that applies to this change?
  □ State the acceptance criteria from PLAN.md

STEP 4 — IMPLEMENT
  □ Write types/schemas first (Pydantic or TypeScript types)
  □ Write the function/component
  □ Write the test alongside (not after)
  □ For compliance functions: write VIOLATION test case first

STEP 5 — SELF-REVIEW (Section 6 checklist — run before presenting)
  □ Three-layer import law not violated
  □ No `any` types, no untyped functions
  □ Error states handled
  □ Test covers both happy path and failure path
  □ AIRULES Rule 47 — nothing on the escalation list was done silently

STEP 6 — DOCUMENT
  □ Update STATE.md current step
  □ Update PLAN.md checkbox for completed item
  □ Log any bugs found to ISSUES.md
  □ Post SESSION SUMMARY
```

---

## 3. Code Generation Templates

### Python — Pipeline Stage Function

```python
# src/pipeline/{stage}/{module}.py
from __future__ import annotations

import structlog
from pydantic import BaseModel

from lib.z3_client import Z3Client          # only if this stage uses Z3
from lib.neo4j_client import Neo4jClient    # only if this stage uses Neo4j
from api.schemas.pipeline import GateResult, ComplianceStatus

logger = structlog.get_logger(__name__)


class {ModuleName}Input(BaseModel):
    model_config = {"frozen": True}  # immutable inputs
    # fields here


class {ModuleName}Output(BaseModel):
    model_config = {"frozen": True}
    # fields here


class {ClassName}:
    """
    One-line description of what this class does.
    Layer: pipeline/{stage}/
    Reads from: [Neo4j / MLflow / Supabase]
    Writes to: [Neo4j / Supabase / nothing]
    """

    def __init__(self, z3_client: Z3Client) -> None:
        self._z3 = z3_client
        self._log = logger.bind(component=self.__class__.__name__)

    async def run(self, input: {ModuleName}Input) -> {ModuleName}Output:
        self._log.info("starting", input_summary=str(input)[:100])
        try:
            # implementation here
            result = await self._do_work(input)
            self._log.info("completed", result_status=result.status)
            return result
        except SpecificExpectedError as e:
            self._log.error("expected failure", error=str(e), input=str(input)[:100])
            raise
        except Exception as e:
            self._log.error("unexpected failure", error=str(e))
            raise

    async def _do_work(self, input: {ModuleName}Input) -> {ModuleName}Output:
        # private implementation
        ...
```

### Python — FastAPI Route Handler

```python
# src/api/routes/{domain}.py
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_current_user, require_role
from api.schemas.{domain} import {Schema}Create, {Schema}Read
from pipeline.{stage}.{module} import {ClassName}

router = APIRouter(prefix="/{domain}", tags=["{domain}"])


@router.post("/", response_model={Schema}Read, status_code=status.HTTP_201_CREATED)
async def create_{entity}(
    body: {Schema}Create,
    current_user=Depends(get_current_user),
    _=Depends(require_role(["compliance_officer"])),  # role restriction
) -> {Schema}Read:
    """One-line description. Role: compliance_officer only."""
    try:
        result = await {ClassName}().run(body)
        return result
    except {DomainSpecificError} as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
```

### Python — Unit Test File

```python
# src/pipeline/{stage}/tests/test_{module}.py
import pytest
from pipeline.{stage}.{module} import {ClassName}
from api.schemas.pipeline import ComplianceStatus
from lib.z3_client import Z3Client


@pytest.fixture
def {component}() -> {ClassName}:
    return {ClassName}(z3_client=Z3Client())


@pytest.fixture
def compliant_input() -> dict:
    """Input that should PASS — describe why"""
    return {}


@pytest.fixture
def violating_input() -> dict:
    """Input that should FAIL — describe which rule and why"""
    return {}


class Test{ClassName}:

    def test_compliant_case_passes(self, {component}, compliant_input) -> None:
        """Happy path — UNSAT result expected"""
        result = {component}.run(compliant_input)
        assert result.status == ComplianceStatus.COMPLIANT
        assert result.proof is not None

    def test_violation_case_fails_with_counterexample(
        self, {component}, violating_input
    ) -> None:
        """CRITICAL — violation path must always be tested"""
        result = {component}.run(violating_input)
        assert result.status == ComplianceStatus.VIOLATION
        assert result.counterexample is not None
        # verify the counterexample contains the expected offending variable
        assert "{offending_feature}" in result.counterexample.variables

    def test_violation_explanation_is_plain_english(
        self, {component}, violating_input
    ) -> None:
        """CO interface never gets raw Z3 — AIRULES Rule 38"""
        result = {component}.run(violating_input)
        assert result.plain_english_explanation is not None
        assert "x!" not in result.plain_english_explanation  # no raw Z3 vars
```

### TypeScript — React Feature Component

```typescript
// frontend/src/features/{interface}/components/{ComponentName}.tsx
import { useState } from 'react'
import type { FC } from 'react'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useAuth } from '@/lib/auth/useAuth'
import type { {DomainType} } from '@/types/{domain}'

interface {ComponentName}Props {
  // props here — no `any`
}

export const {ComponentName}: FC<{ComponentName}Props> = ({ ...props }) => {
  const { role } = useAuth()

  // Loading state — AIRULES Rule 12
  if (isLoading) {
    return <LoadingSpinner label="Loading {description}..." />
  }

  // Error state — AIRULES Rule 12
  if (isError) {
    return (
      <div role="alert" className="text-red-600 text-sm p-4 bg-red-50 rounded-md border border-red-200">
        {errorMessage}
      </div>
    )
  }

  // Empty state — AIRULES Rule 12
  if (!data || data.length === 0) {
    return (
      <div className="text-neutral-400 text-sm text-center py-8">
        No {description} found.
      </div>
    )
  }

  return (
    <div>
      {/* component content */}
    </div>
  )
}
```

### TypeScript — Custom Hook

```typescript
// frontend/src/features/{interface}/hooks/use{HookName}.ts
import { useQuery } from '@tanstack/react-query'
import { {apiFunction} } from '@/lib/api/{domain}'
import type { {ReturnType} } from '@/types/{domain}'

export function use{HookName}(id?: string) {
  const query = useQuery({
    queryKey: ['{entity}', id],
    queryFn: () => {apiFunction}(id!),
    enabled: !!id,
    staleTime: 30_000,
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  }
}
```

---

## 4. Debugging Protocol

When something is broken, run this exact sequence. Do not skip steps.

```
1. CHECK ISSUES.md FIRST
   Has this exact error or class of error been logged before?
   If yes → apply the documented solution before debugging from scratch.

2. CHECK RECENT CHANGES
   git log --oneline -10
   git diff HEAD~1 HEAD -- {affected_file}
   Did a recent commit introduce this? Revert and confirm if unsure.

3. ISOLATE THE LAYER
   Which of the three layers is broken?
   /lib/       → client configuration, external service connectivity
   /pipeline/  → business logic, Z3 formula, state machine
   /features/  → UI rendering, data fetching, auth

4. FOR Z3 ERRORS specifically:
   a. Run `python scripts/verify_z3_install.py` — is Z3 installed correctly?
   b. Is the formula well-formed? Run `ingestion/validator.py` on the formula manually
   c. Is it SAT or UNSAT? Log the raw Z3 result before any transformation
   d. Is the counterexample being parsed correctly? Log raw `model()` output

5. FOR FASTAPI ERRORS:
   a. Check `/docs` — does the route appear in Swagger?
   b. Check dependency chain — is `get_current_user` failing?
   c. Check Pydantic validation — is the request body matching the schema?
   d. Check structured logs — what did `logger.error()` capture?

6. FOR REACT ERRORS:
   a. Is it a type error? Fix the TypeScript type first, not the runtime behavior
   b. Is it a missing state? Check loading/error/empty branches all render
   c. Is it a stale query? Add `console.log(query)` temporarily, check `status`
   d. Is it an auth issue? Check `useAuth().role` matches expected value

7. DOCUMENT IN ISSUES.md
   Every non-trivial bug gets logged:
   - What broke
   - What caused it
   - How it was fixed
   - How to prevent it
```

---

## 5. Standard Prompts

Copy these exactly. Fill `[BRACKETS]` with real values.

---

### 5a. SESSION START — Short (use this 90% of the time)

```
Project: Rego — FinTech MLOps platform for Continuous Regulatory Compliance Reasoning
Stack: Python 3.11 + FastAPI + Z3 SMT Solver + OpenRouter (Claude 3.5 Sonnet) + Neo4j Aura + Supabase + React 18 + TypeScript
Jurisdiction: India RBI Master Directions on Digital Lending 2022

Read STATE.md first. Current position:
- Stage: [X], Sub-stage: [Y] — [name]
- Last completed: [one sentence]
- Next action: [exact next action from STATE.md]

Key rules (full list in AIRULES.md):
- Z3 is the ONLY engine in CI/CD compliance gates — never LLM
- LLM is offline/batch only — never in hot path
- Three-layer import law: /features/ ← /pipeline/ ← /lib/ (no reverse)
- Human approval required before any rule enters pipeline
- Certificates are immutable once written

Today's task: [what you want to build]
```

---

### 5b. SESSION START — Full (use for complex sessions or new features)

```
Project: Rego — FinTech MLOps platform for Continuous Regulatory Compliance Reasoning

You have access to these finalized project docs — read all that apply before starting:
- PRIVATE/PRD.md — what the product is, 7 core features, HCI principles
- PRIVATE/TECH.md — full stack with pinned versions, Z3 rationale, forbidden packages
- PRIVATE/ARCHITECTURE.md — three-layer structure (/features/ /pipeline/ /lib/), file placement law, naming conventions
- PRIVATE/DESIGN.md — Rego Indigo palette, two interfaces (light mode both), compliance status badge contract
- PRIVATE/AIRULES.md — 47 non-negotiable rules. Most critical: Rules 1-5 (Z3/LLM/gate/cert/approval), Rule 8 (import law), Rule 38 (CO never sees raw Z3), Rule 39 (two-click approval), Rule 47 (escalation list)
- PRIVATE/CONSTRAINTS.md — $0 budget, free tier only, escalation format
- PRIVATE/TESTING.md — bilateral tests required for all compliance functions, real Z3 never mocked
- PRIVATE/PLAN.md — 6-stage roadmap, ~120 checklist items, acceptance criteria per feature
- PRIVATE/STATE.md — current position (read this first before anything else)
- PRIVATE/ISSUES.md — known bugs and solutions

Current position (from STATE.md):
- Stage: [X], Sub-stage: [Y] — [name]
- Last completed: [one sentence]
- Blockers: [or None]

Today's task: [what you want to build]
File(s) to create/modify: [list from ARCHITECTURE.md]
Acceptance criteria: [from PLAN.md]
```

---

### 5c. NEW FEATURE

```
Implement Feature [X.Y] from PLAN.md: [feature name]

Context:
- This is Stage [X], Sub-stage [Y] of the Rego project
- Depends on: [previous feature or 'nothing — first feature']
- Layer: [/pipeline/{stage}/ or /features/{interface}/ or /lib/]

Files to create:
1. [src/pipeline/.../file.py] — [one-line purpose]
2. [src/pipeline/.../tests/test_file.py] — [bilateral: compliant + violation]

Acceptance criteria (from PLAN.md):
- [copy exact criteria from PLAN.md]

Rules that apply (from AIRULES.md):
- [relevant rules — e.g. "Rule 2: LLM offline only" if this touches ingestion]
- [Rule 15: Z3 calls must log 5 specific fields — if Z3 involved]
- [Rule 38: CO never sees raw Z3 — if this produces explanations]

Write types first, then implementation, then tests.
Post SESSION SUMMARY when done.
```

---

### 5d. BUG REPORT

```
Bug in Rego — [one-line description]

File: [src/pipeline/.../file.py or frontend/src/.../Component.tsx]
Layer: [/pipeline/ or /features/ or /lib/]

Error:
[paste exact error message or stack trace]

Expected behavior:
[what should happen — reference PLAN.md acceptance criteria if relevant]

Actual behavior:
[what is happening]

Reproduction:
[exact steps or command to reproduce]

What I've checked already:
- [ ] ISSUES.md — [found / not found similar issue]
- [ ] Recent git changes — [relevant / not relevant]
- [ ] Layer isolated to: [which file/function]

AIRULES rules that might be relevant:
[e.g. "Rule 4 — certificates are immutable — could this be a double-write?"]

Do not fix anything else while fixing this. Scope is this bug only.
After fixing: write a regression test that would have caught this, then fix.
```

---

### 5e. DEEPSEEK CODE REVIEW

```
Code review request for Rego — compliance-critical file.

Project context:
Rego is a FinTech MLOps platform where Z3 SMT Solver formally verifies that ML models
comply with India RBI Master Directions on Digital Lending 2022. This is a legal
compliance system — bugs have regulatory consequences.

Stack: Python 3.11, FastAPI, Z3 4.12.6.0, Pydantic v2, Supabase, Neo4j

File to review: [filename]
Layer: [pipeline/ci/ or pipeline/cd/ or lib/]
Purpose: [one-line description]

Focus your review on:
1. Correctness of Z3 formula encoding (if applicable) — does it actually capture the regulatory rule?
2. Error handling — are all failure paths caught and logged?
3. Security — any PII in logs? Any input that could inject into Z3 or LLM?
4. Immutability — if this touches certificates, is there any write path that could overwrite?
5. Type safety — any implicit type coercions?
6. Test coverage — does the existing test cover the VIOLATION case, not just COMPLIANT?

Non-negotiable rules to check against:
- Z3 is the only engine in compliance gates — no heuristics, no LLM verdicts
- LLM is never in the hot path
- Certificates are write-once — no UPDATE path
- Human approval required before any rule activates
- CO interface never receives raw Z3 output

Output format:
## Critical issues (must fix before merge)
## Warnings (should fix)
## Suggestions (optional improvements)
## Verdict: APPROVE / REQUEST CHANGES

[paste file content here]
```

---

### 5f. CONCEPT QUESTION (ChatGPT / Gemini)

```
Quick concept question — no code needed, just explanation.

Context: I'm building a FinTech MLOps platform that uses Z3 SMT Solver to formally
verify that ML loan approval models comply with RBI regulations. I'm not asking you
to write code for this project.

Question: [your question]

Keep it under 200 words. I need the concept, not an implementation.
```

---

### 5g. SESSION END

```
Session ending. Please do the following before we close:

1. Update STATE.md:
   - Mark completed sub-stage checkboxes
   - Set Current Step to next unchecked item
   - Set Next Action to the specific next thing (file + action)
   - Update Last Updated to now
   - Add row to Recent Changes table

2. Update PLAN.md:
   - Mark completed checklist items with ✅
   - Note if any acceptance criteria were only partially met

3. Update ISSUES.md:
   - Log any bugs discovered this session (even if fixed)
   - Log any gotchas or non-obvious decisions made

4. Post SESSION SUMMARY:
   ✅ Done: [list]
   📍 Now at: Stage [X], Sub-stage [Y] — [name]
   ➡️  Next: [exact next action]
   ⚠️  Open: [blockers or 'None']
   🕐 STATE.md updated [timestamp]
```

---

## 6. Self-Review Checklist

Run this mentally before presenting any code as complete.

### For ALL code:
```
□ File is in the correct layer per ARCHITECTURE.md Section 2
□ No imports cross layer boundaries (/features/ ↔ /pipeline/ forbidden)
□ No `any` type in TypeScript, no untyped function in Python
□ Every async function has try/except with structured logging
□ No hardcoded strings for status values (use constants/enums)
□ New env var → added to .env.example in same change
□ New package → added to TECH.md first (if applicable)
```

### For compliance pipeline code specifically:
```
□ Z3 is doing the compliance verdict — not LLM, not heuristics
□ Z3 call logs: input formula hash, UNSAT/SAT result, duration, rule IDs (AIRULES Rule 15)
□ VIOLATION case tested — not just happy path
□ Plain English explanation generated for every violation (AIRULES Rule 38)
□ No raw Z3 variable names (x!, !val!) visible to CO interface
□ Certificate writes are fire-once — no update path exists
□ Approval state machine cannot skip human action
```

### For React components:
```
□ Loading state renders with descriptive label (not just spinner)
□ Error state renders inline (not just toast)
□ Empty state renders (not blank screen)
□ Compliance status uses StatusBadge component — not custom color
□ Color is never the only differentiator — text label always present
□ CO interface has zero technical jargon
□ MLE interface shows Z3 details that CO interface hides
```

### For tests:
```
□ Test name describes behavior: test_violating_model_fails_with_counterexample ✓
□ Test name does not describe implementation: test_check_method ✗
□ Real Z3 used — not mocked (TESTING.md Section 7)
□ Both COMPLIANT and VIOLATION fixtures exist for compliance functions
□ Invalid state machine transitions tested
□ Test is colocated in correct tests/ subfolder
```

---

## 7. Definition of Done

### Feature Done ✅
A feature from PLAN.md is done when ALL of the following are true:
- [ ] All implementation checklist items checked in PLAN.md
- [ ] Acceptance criteria from PLAN.md verified manually
- [ ] Unit tests pass (bilateral: compliant + violation for pipeline code)
- [ ] Integration test passes (if route or DB involved)
- [ ] Linters pass: `ruff check src/`, `mypy src/`, `npm run lint`
- [ ] CI green on latest commit
- [ ] STATE.md updated, PLAN.md checkbox marked
- [ ] No new entries in ISSUES.md that are unfixed

### Bug Fix Done ✅
A bug fix is done when:
- [ ] Regression test written that reproduces the bug (and was red before fix)
- [ ] Regression test is green after fix
- [ ] Root cause documented in ISSUES.md
- [ ] No other behavior changed (run full test suite)
- [ ] AIRULES Rule 45 checked — nothing extra was changed

### Refactor Done ✅
A refactor is done when:
- [ ] All existing tests still pass (zero new failures)
- [ ] No behavior changed — only structure
- [ ] Three-layer import law still holds after refactor
- [ ] PLAN.md acceptance criteria for affected features still met
- [ ] CI green

---

## 8. Escalation Rules

Stop coding and ask the human explicitly when:

| Situation | What to say |
|-----------|-------------|
| Asked to bypass a compliance gate | "⚠️ ESCALATE — AIRULES Rule 47: this is on the forbidden list. Confirm you understand the legal implication before I proceed." |
| Asked to auto-approve a rule | "⚠️ ESCALATE — AIRULES Rule 5: human approval is required. I cannot implement auto-approval." |
| Asked to write compliance verdict using LLM | "⚠️ ESCALATE — AIRULES Rule 2: LLM cannot produce compliance verdicts. Z3 does this. Do you want me to implement the Z3 path instead?" |
| Asked to modify a certificate | "⚠️ ESCALATE — AIRULES Rule 4: certificates are immutable. A modification would create a new certificate for a rollback. Is that what you want?" |
| Need to add a new package | "⚠️ CONSTRAINT — package [X] is not in TECH.md. I need to add it there first. Reason: [why needed]. Shall I update TECH.md and proceed?" |
| Need to add a paid service | "⚠️ CONSTRAINT — [service] has a cost implication. Budget is $0. Free alternative: [X]. Proceed with free alternative?" |
| Z3 formula encoding is ambiguous | "⚠️ UNCERTAIN — the RBI regulation §[X] could be encoded as [formula A] or [formula B]. They have different implications: [explain]. Which interpretation is correct?" |
| Conflict between two docs | "⚠️ DOC CONFLICT — [AIRULES.md Rule X] and [ARCH.md Section Y] appear to conflict on [topic]. Which takes precedence?" |
| Task requires >5 files | "⚠️ SCOPE — this task touches [N] files. That's larger than one session. Shall I break it into: (1) [sub-task A], (2) [sub-task B]?" |

**The meta-rule:** When in doubt about anything compliance-related — stop and ask. A wrong guess in a legal compliance system is worse than a question.

---

*SKILLS.md is FINALIZED.*
*Section 5 (Standard Prompts) is the most used section — copy-paste those templates.*
*The goal of this doc: zero context re-explanation at the start of every session.*
