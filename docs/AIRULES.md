# AIRULES.md — Non-Negotiable AI Rules
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: FINALIZED
# ============================================================
# Every AI tool working on this project must read this file
# before writing a single line of code.
# These rules are not suggestions. They are the contract.
# Violation of any 🔴 rule is grounds to stop and ask.
# ============================================================

## 🔴 Absolute Rules
*Never break. No exceptions. No "just this once."*

**1. Z3 SMT Solver is the ONLY engine permitted in CI/CD compliance gates.**
No heuristic checks, no LLM-based compliance verdicts, no probabilistic rule matching in any deployment gate. Z3 or nothing. If Z3 cannot verify it, the gate fails — it does not pass.

**2. LLM is offline/batch only. Never in the hot path. LLM output is always a candidate — never a final rule.**
OpenRouter/LLM calls are permitted only in `pipeline/ingestion/extractor.py` (rule extraction) and plain-English explanation generation. LLM is structurally forbidden from: `pipeline/ci/`, `pipeline/cd/`, any route handler that runs during model deployment, any function that contributes to a compliance verdict.

The trust chain that resolves the apparent contradiction ("LLMs hallucinate" vs "LLM generates the rules") is:
**LLM drafts candidate → Z3 validates structure → human validates semantic intent → rule activates.**
LLM is trusted to produce a *plausible draft*, not a *correct rule*. Z3 checks structural validity. The human checks whether the formula captures the regulation's intent. Both checks must pass before a rule is active. "Garbage in → perfectly verified garbage out" is impossible because the human gate sits between LLM output and Z3 usage as a compliance standard.

**3. A model that fails CI gates must never reach production.**
There is no override flag, no `--force-deploy`, no environment variable that bypasses the compliance gate. If you are ever asked to add a bypass, stop and escalate. This is a legal compliance system — a bypass is a liability.

**4. Proof certificates are immutable once written.**
`cd/certificate.py` writes to Supabase exactly once per deployment. There is no update path, no patch endpoint, no "re-certify" function. If you find yourself writing an UPDATE query against the certificates table — stop. A rollback generates a new certificate for the rolled-back version; it does not modify the previous one.

**5. Human approval is required before any rule enters the pipeline.**
`pipeline/ingestion/approver.py` enforces a state machine: `extracted → z3_validated → pending_approval → approved → active`. No rule may transition from `pending_approval` to `active` without a human action (CO clicks approve). The Z3 well-formedness check (`z3_validated` state) runs automatically before the rule is ever shown to the human — a malformed formula never reaches the approval queue. AI must never auto-approve a rule, even in tests.

**6. `SUPABASE_SERVICE_KEY` never leaves the FastAPI backend process.**
It must not appear in: React source, environment variables prefixed `VITE_`, any API response body, any log line. If you are writing code that sends this key to the frontend — stop immediately.

**7. Never add a package not listed in TECH.md.**
Not as a dev dependency, not "just for one script", not as a temporary fix. Add the package to TECH.md first, state the reason, then install. This rule exists because every new dependency is a potential attack surface in a financial compliance system.

**8. The three-layer import law is absolute.**
`/features/` never imports from `/pipeline/`. `/pipeline/` never imports from `/features/`. Both import from `/lib/`. `/lib/` imports from nothing internal. This is enforced by `ruff` in CI — a violation fails the build. Do not suppress the ruff rule.

**9. Every new environment variable must be added to `.env.example` in the same commit.**
No exceptions. A variable that exists in `.env` but not in `.env.example` is invisible to every other developer and every deployment environment. This rule has no grace period.

**10. TypeScript: no `any`. Python: no untyped function signatures.**
TypeScript — `any` is banned. Use `unknown` with a type guard if the type is genuinely unknown. Python — every function must have type hints on all parameters and return values. `mypy` runs in CI; untyped code fails the build.

---

## 🟡 Code Quality Rules
*Every PR must pass these. No merge without compliance.*

**11. Every async Python function must have try/except. No swallowed errors.**
```python
# Wrong
async def extract_rules(text: str) -> list[Rule]:
    result = await llm_client.extract(text)
    return result

# Right
async def extract_rules(text: str) -> list[Rule]:
    try:
        result = await llm_client.extract(text)
        return result
    except LLMExtractionError as e:
        logger.error("Rule extraction failed", rule_text=text[:100], error=str(e))
        raise
```

**12. Every React component must handle loading state, error state, and empty state.**
A component that fetches data and only renders the happy path is incomplete. Every `useQuery` or `axios` call must have corresponding `isLoading`, `isError`, and empty data branches rendered in the UI. Compliance officers must never see a blank screen.

**13. Python files: max 300 lines. React components: max 200 lines.**
If a file exceeds this, it has more than one responsibility. Split it. The only exception is generated files (migration files, seed scripts) — these may be longer.

**14. No hardcoded strings for rule IDs, regulation names, or status values.**
Wrong: `if status === 'compliant'`. Right: `import { COMPLIANCE_STATUS } from '@/lib/utils/constants'`. All domain constants live in `frontend/src/lib/utils/constants.ts` and `src/api/schemas/` enums. This prevents the "compliant" vs "COMPLIANT" bug that silently breaks status displays.

**15. Every Z3 call must log: input formula hash, result (UNSAT/SAT), duration, rule IDs checked.**
```python
logger.info(
    "Z3 check complete",
    formula_hash=hash_formula(formula),
    result="UNSAT" if is_compliant else "SAT",
    duration_ms=elapsed,
    rules_checked=[r.rule_id for r in active_rules],
    model_version=model_version,
)
```
This log is the audit trail for every compliance decision.

**16. All Pydantic models use `model_config = ConfigDict(frozen=True)` for certificate schemas.**
Proof certificates are immutable data. Frozen Pydantic models enforce this at the Python level — a mutation attempt raises an error rather than silently succeeding.

**17. Git commits follow Conventional Commits format.**
`feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:` — prefix required on every commit. CI lints commit messages. `feat: add Z3 symbolic check for RBI §4.1` ✓. `updated stuff` ✗.

**18. No `console.log` in committed React code. No `print()` in committed Python code.**
Use structured logging: Python → `structlog`, React → remove before commit. CI grep catches these.

**19. Every function that calls the Z3 client must have a corresponding unit test with both a COMPLIANT and a VIOLATION fixture.**
A Z3 check with only a passing test is half-tested. The violation path (where Z3 returns SAT + counterexample) is the most important path in the system.

**20. `poetry.lock` and `package-lock.json` must be committed and kept up to date.**
No `--no-lockfile` installs. Deterministic builds are non-negotiable for a compliance system. If CI fails because of a lockfile mismatch, fix the lockfile — do not skip it.

---

## 🔵 Architecture Rules
*Structural constraints. Reference ARCHITECTURE.md for full detail.*

**21. New files go in the correct layer or don't get created.**
Before creating any file: open ARCHITECTURE.md Section 2 (File Placement Rules) and confirm the location. A `symbolic_check.py` that lives in `/lib/` instead of `/pipeline/ci/` is in the wrong place regardless of whether it "works."

**22. Pipeline stages are isolated. Each stage's logic lives only in its own directory.**
`pipeline/ci/` does not call functions defined in `pipeline/cd/`. If logic is needed across stages, it belongs in `/lib/`. Stages communicate through data contracts (Pydantic schemas), not direct function calls.

**23. FastAPI route handlers contain no business logic.**
Route handlers validate input (via Pydantic), call one service function, and return the response. Business logic lives in the pipeline layer or lib layer. A route handler that is longer than 20 lines probably has business logic that needs to be extracted.

**24. Domain naming is enforced. Use ARCHITECTURE.md Section 3 naming table.**
`rule` not `policy`. `certificate` not `report`. `regulation_drift` not `law_change`. `symbolic_check` not `logic_check`. `lineage` not `history`. Every variable name, function name, and API endpoint must use the canonical domain vocabulary.

**25. GitHub Actions workflows are the only permitted orchestrators.**
No Celery, no Redis queues, no custom schedulers, no cron jobs outside GitHub Actions. The CT trigger (`ct/trigger.py`) fires a GitHub Actions workflow dispatch event. Pipeline orchestration is observable — every run has a GitHub Actions log.

**26. Path aliases are mandatory. Relative imports beyond one level are forbidden.**
`from pipeline.ci.symbolic_check import Z3ComplianceChecker` ✓. `from ../../lib.z3_client import Z3Client` ✗. TypeScript: `import { useAuth } from '@/lib/auth/useAuth'` ✓. `import { useAuth } from '../../../lib/auth/useAuth'` ✗.

**27. Unit tests are colocated. Integration tests live in `/tests/integration/`.**
`pipeline/ci/symbolic_check.py` → `pipeline/ci/tests/test_symbolic_check.py`. Full pipeline E2E → `tests/integration/test_pipeline_e2e.py`. Never put a unit test in the top-level tests folder.

**28. Docker is used for local development parity. Never "it works on my machine."**
Local dev runs via `docker-compose.yml`. If a dependency (Neo4j, Supabase local) requires Docker to run locally, that is the correct setup. Never develop against a production Neo4j or Supabase instance.

---

## 🛡️ Security Rules
*Financial compliance system. These are non-negotiable.*

**29. Regulatory text input is sanitized before LLM submission.**
The regulatory text field (CO drag-and-drop interface) strips HTML, control characters, and content exceeding 50,000 characters before sending to OpenRouter. Prompt injection via regulatory text is a real attack vector. Sanitize at the API boundary, not in the frontend.

**30. All API endpoints require authentication. No unauthenticated routes except `/health`.**
Supabase JWT validation runs on every request via FastAPI dependency injection (`dependencies.py`). A route without `Depends(get_current_user)` is a security hole. `/health` and `/health/z3` are the only permitted exceptions.

**31. Role-based access is enforced at the API layer, not just the frontend.**
`compliance_officer` role: read regulations, approve/reject rules, download certificates. `ml_engineer` role: read pipeline status, trigger pipeline, read model versions. `cto` role: read-only everything. Frontend routing enforces role — but the API enforces it too. Never trust the frontend for authorization.

**32. Z3 formula inputs are validated for well-formedness before solver execution.**
`ingestion/validator.py` runs a Z3 parse check on every LLM-generated rule before it touches the knowledge graph. A malformed formula fed to Z3 can cause unexpected solver behavior. Parse first, run never if invalid.

**33. Proof certificate HMAC signatures are verified on every read.**
When a certificate is retrieved from Supabase, `cd/certificate.py` re-verifies the HMAC against `PROOF_CERT_SECRET` before returning it. A certificate that fails HMAC verification is flagged as tampered and must not be served. This detects database tampering.

**34. No PII in logs.**
Financial ML systems process loan application data. Log the model version, rule IDs, compliance result, and timing. Never log: applicant names, PAN numbers, Aadhaar numbers, income figures, or any data that could identify an individual. Use applicant IDs (hashed) if correlation is needed.

**35. API rate limiting is enabled on all regulatory ingestion endpoints.**
The `/api/regulations` POST endpoint (which triggers LLM extraction) is rate-limited to 10 requests per minute per user. OpenRouter charges per token — an unprotected endpoint is a billing attack surface. Implement via FastAPI middleware.

**36. `.env` is in `.gitignore`. Verify this on every new machine setup.**
Script: `python scripts/verify_z3_install.py` includes a `.env` gitignore check. If `.env` appears in `git status`, the script exits with a non-zero code and prints a warning. This check runs in CI.

---

## 🎨 UI/UX Rules
*Reference DESIGN.md for full detail. These are the enforced minimums.*

**37. Compliance status must always display BOTH color AND text label. Never color alone.**
A green dot without the word "Compliant" is not accessible and not legally sufficient. Every status display uses the `StatusBadge` component from `features/compliance-officer/components/ComplianceBadge.tsx`. Bespoke status indicators are forbidden.

**38. The compliance officer interface never shows raw Z3 output, proof hashes, or technical error messages.**
Z3 produces output like `[x!0 = 0.3, postal_code_weight = 1.2]`. This is a counterexample. In the CO interface it becomes: *"This model uses postal code to influence loan decisions, which violates RBI Master Direction §4.1.c (prohibited use of geographic proxies)."* Translation happens in `pipeline/ci/reporter.py`. The CO interface renders the translation only.

**39. The approve/reject action for regulatory rules requires explicit user intent — no single-click approval.**
The approval flow: (1) CO sees the LLM-generated rule translation, (2) CO reads the source text, (3) CO clicks "Approve" — which opens an inline confirmation, (4) CO confirms. Two deliberate actions minimum. This is an HCI principle from PRD.md: *"AI suggests, human decides."* No shortcut.

**40. Every loading state shows what is loading, not just a spinner.**
Wrong: generic `<LoadingSpinner />`. Right: `<LoadingSpinner label="Running symbolic check against 12 rules..." />`. Compliance officers and ML engineers need to know what the system is doing at all times — PRD.md Visibility principle.

**41. Form validation errors appear inline next to the field, never only as a toast.**
Toasts disappear. Inline errors persist until corrected. For a compliance officer uploading regulatory text, a toast error that says "Invalid format" is gone before they can act on it. Inline errors are mandatory for all form fields.

**42. The MLE interface uses `body-md` (14px) density. The CO interface uses `body-lg` (16px) density.**
Never apply MLE density to CO screens. Never apply CO density to MLE screens. These are different cognitive environments — see DESIGN.md Section 8.

---

## 🔄 Workflow Rules
*How AI tools behave, communicate, and escalate on this project.*

**43. Read STATE.md first, every session. Confirm current step before writing any code.**
Session start protocol: read STATE.md → state the current stage and step out loud → ask "Has anything changed since [last updated]?" → wait for confirmation → proceed. A session that starts coding without confirming STATE.md is working blind.

**44. Post a SESSION SUMMARY before ending every session.**
Format:
```
✅ Done: [list of completed items]
📍 Now at: [Stage X, Step Y]
➡️ Next: [specific next action]
⚠️ Open: [blockers or decisions needed, or 'None']
🕐 STATE.md updated [timestamp]
```
No session ends without this block. STATE.md, PLAN.md, and ISSUES.md are updated automatically.

**45. Never implement more than what was asked.**
If asked to implement `pipeline/ci/symbolic_check.py`, implement that file. Do not also refactor `pipeline/ct/trainer.py` because you noticed something, do not add a new endpoint to `routes/pipeline.py` because it "seemed useful," do not install a new package because it "would help." Scope creep in a compliance system introduces unreviewed changes to legally critical code.

**46. When uncertain about a compliance decision in code, stop and ask. Never guess.**
This applies specifically to: Z3 formula encoding (how to translate a regulation into formal logic), certificate generation logic, the approval state machine, and any code that determines whether a model is compliant. These are the legal core of the system. A wrong guess is worse than a question.

**47. Escalate immediately if asked to do any of the following:**
- Bypass or disable a compliance gate
- Auto-approve a regulatory rule without human review
- Write a compliance verdict using LLM output (not Z3)
- Delete or modify a proof certificate record
- Add a new deployment path that skips `pipeline/cd/`
- Hardcode a compliance status (e.g., `return ComplianceStatus.COMPLIANT` unconditionally)

These are not edge cases — they are the exact failure modes that make financial ML systems illegal. Stop, quote this rule, and ask the human to confirm they understand the implication before proceeding.

---

## ⚙️ Project-Specific Rules
*Domain rules specific to Rego's position as a legal compliance system.*

**Not listed separately — all 47 rules above are project-specific.**

Rules 1–5 encode the neuro-symbolic pipeline contract (Rule 2 includes the LLM→Z3→human trust chain).
Rules 29–36 encode the FinTech/RBI security posture.
Rules 37–42 encode the HCI compliance interface contract.
Rules 43–47 encode the human-in-the-loop workflow requirement.

There are no generic rules in this document. Every rule traces back to a specific decision in PRD.md, TECH.md, ARCHITECTURE.md, or DESIGN.md. If a rule feels generic — it should be made more specific or removed.

---

## Rule Traceability Index

| Rule | Source Document | Section |
|------|----------------|---------|
| 1 | TECH.md | Z3 scope — symbolic reasoning only in gates |
| 2 | TECH.md + PRD.md | LLM scope (offline only) + LLM→Z3→human trust chain |
| 3 | PRD.md | Feature 3 (Compliance-Gated CD) |
| 4 | PRD.md | Section 2 correction (cert per deployment, immutable) |
| 5 | PRD.md + AIRULES audit | HCI Principle: Control + 5-state machine |
| 6 | TECH.md | Environment Variables — service key never leaves backend |
| 7 | TECH.md | Forbidden Packages — TECH.md first, then install |
| 8 | ARCHITECTURE.md | Section 0 + Section 7 Decision 1 — three-layer import law |
| 9 | TECH.md | Environment Variables — .env.example parity |
| 10 | TECH.md | Python 3.11 typed, TypeScript strict |
| 11–20 | TECH.md + Stack | Stack-derived code quality rules |
| 21–28 | ARCHITECTURE.md | Sections 0–7 — structural constraints |
| 29–36 | PRD.md § Constraints + TECH.md | FinTech/RBI security posture |
| 37–42 | DESIGN.md | Sections 6–9 — UI/UX interface standards |
| 43–47 | PRD.md HCI Principles + STATE.md protocol | Workflow rules |

---

*AIRULES.md is FINALIZED. Every AI tool reads this file before every session.*
*Rules are added only by updating this file AND the relevant source doc.*
*Rule count: 47 rules across 7 categories. Rule 2 contains the LLM↔Z3 trust chain resolution.*
