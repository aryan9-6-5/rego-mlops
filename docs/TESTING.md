# TESTING.md — Test Strategy & Standards
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: FINALIZED
# ============================================================
# Every AI tool reads this before writing tests or marking
# anything "done". "It works on my machine" is not a test.
# In a legal compliance system, an untested compliance path
# is a liability, not a feature.
# ============================================================

## 1. Testing Philosophy

**"If it touches compliance, it has a test. No exceptions."**

Rego is a system where bugs have legal consequences — a false COMPLIANT verdict, a tampered certificate, a silently bypassed gate. The testing strategy reflects this: the symbolic reasoning pipeline (Z3 checks, certificate generation, approval state machine) has exhaustive test coverage. The UI and utility code follows pragmatic coverage targets. Nothing ships without a passing CI gate.

**What "tested" means on this project:**
A feature is done when:
1. The happy path has a test
2. The failure path has a test (especially for compliance gates — the VIOLATION case is more important than the COMPLIANT case)
3. The test runs green in CI
4. Edge cases that could produce a false compliance verdict have explicit tests

---

## 2. Test Pyramid

```
         ╱─────────────╲
        ╱   E2E Tests    ╲         ~10 tests
       ╱  (Playwright)    ╲        Critical user flows only
      ╱─────────────────────╲
     ╱   Integration Tests   ╲    ~40 tests
    ╱  (pytest + httpx)       ╲   API routes, DB ops, pipeline E2E
   ╱─────────────────────────── ╲
  ╱        Unit Tests            ╲  ~120 tests
 ╱  (pytest + Vitest)             ╲ Z3 logic, rule extraction, components
╱─────────────────────────────────╲
```

**Rationale for this balance:**

| Layer | Count | Why |
|-------|-------|-----|
| Unit | ~120 | Z3 checks, LLM extraction, certificate logic — every compliance function needs bilateral testing (COMPLIANT + VIOLATION) |
| Integration | ~40 | FastAPI routes with real Supabase test instance, pipeline stage chaining, Neo4j lineage writes |
| E2E | ~10 | Only the 3 critical user flows that an auditor would walk through — not every click path |

**Why so few E2E?** Rego is a pipeline orchestration tool, not a consumer app. The meaningful behavior lives in the Python pipeline, not in browser interactions. E2E tests cover the flows that a compliance officer or auditor would perform. CI time is precious ($0 budget, 2,000 GH Actions minutes/month).

---

## 3. Unit Tests

### What MUST always have unit tests

**Python — mandatory coverage:**

| Module | What to test | Why critical |
|--------|-------------|-------------|
| `pipeline/ci/symbolic_check.py` | Every Z3 rule check — both UNSAT (compliant) AND SAT (violation + counterexample) | False COMPLIANT verdict is a legal liability |
| `pipeline/ingestion/extractor.py` | LLM output → Rule object parsing, malformed output handling | Bad rule extraction corrupts the knowledge graph |
| `pipeline/ingestion/validator.py` | Z3 well-formedness check on generated rules, rejection of invalid formulas | Invalid formula fed to Z3 causes solver errors |
| `pipeline/ingestion/approver.py` | All state machine transitions: extracted→pending, pending→approved, pending→rejected, invalid transitions | Human approval gate is Rule 5 in AIRULES.md |
| `pipeline/cd/certificate.py` | Certificate generation, HMAC signing, HMAC verification, tamper detection | Certificate integrity is the legal output of Rego |
| `pipeline/cd/lineage.py` | model↔regulation lineage creation, lineage query correctness | Lineage is what makes certificates meaningful |
| `pipeline/ct/drift_detector.py` | New rule detection, amended rule detection, no-change detection | CT trigger must fire exactly when needed, never spuriously |
| `lib/z3_client.py` | `prove()` returns correct ProofResult, `counterexample()` returns Counterexample with variable assignments | Z3 client is the trust foundation |
| `lib/llm_client.py` | OpenRouter call, fallback model switch on 429, retry with backoff | LLM failures must not crash the ingestion pipeline |

**TypeScript — mandatory coverage:**

| Component/Hook | What to test |
|---------------|-------------|
| `ComplianceBadge.tsx` | Renders correct color + text for all 4 statuses. Never renders color without text label |
| `useComplianceStatus.ts` | Returns correct status from API response, handles loading, handles error |
| `RuleTranslationCard.tsx` | Approve/reject buttons present, confirmation step required before approve fires |
| `lib/utils/constants.ts` | All status enum values match backend Pydantic enum values exactly |
| `lib/api/certificates.ts` | HMAC verification failure returns error state (not silent) |

### What does NOT need unit tests

- Pydantic schema definitions (if they have no custom validators)
- FastAPI route handlers shorter than 10 lines (covered by integration tests)
- Tailwind class strings and pure layout components
- `__init__.py` files
- Migration files
- Seed scripts (test the seeded state, not the script)
- `docker-compose.yml` and infrastructure config

### File naming and location convention

```
# Python unit tests — colocated
src/pipeline/ci/symbolic_check.py
src/pipeline/ci/tests/test_symbolic_check.py   ← colocated in tests/ subfolder

# React unit tests — colocated
frontend/src/features/compliance-officer/components/ComplianceBadge.tsx
frontend/src/features/compliance-officer/components/ComplianceBadge.test.tsx  ← same dir

# Fixtures — colocated with their tests
src/pipeline/ingestion/tests/fixtures/rbi_sample_rule_valid.txt
src/pipeline/ingestion/tests/fixtures/rbi_sample_rule_malformed.txt
```

### Python unit test template

```python
# src/pipeline/ci/tests/test_symbolic_check.py
import pytest
from pipeline.ci.symbolic_check import Z3ComplianceChecker
from api.schemas.pipeline import GateResult, ComplianceStatus
from lib.z3_client import Z3Client


@pytest.fixture
def checker() -> Z3ComplianceChecker:
    return Z3ComplianceChecker(z3_client=Z3Client())


@pytest.fixture
def compliant_model_constraints() -> dict:
    """Model that does NOT use postal code — should pass RBI §4.1.c"""
    return {
        "features_used": ["income", "credit_score", "loan_amount"],
        "decision_boundary": 0.5,
    }


@pytest.fixture
def violating_model_constraints() -> dict:
    """Model that uses postal code — should FAIL RBI §4.1.c"""
    return {
        "features_used": ["income", "credit_score", "postal_code"],
        "decision_boundary": 0.5,
    }


class TestZ3ComplianceChecker:

    def test_compliant_model_returns_unsat(
        self, checker: Z3ComplianceChecker, compliant_model_constraints: dict
    ) -> None:
        """UNSAT = no violation found = model is compliant"""
        result: GateResult = checker.check(
            model_constraints=compliant_model_constraints,
            rule_id="RBI-MD-2022-§4.1.c",
        )
        assert result.status == ComplianceStatus.COMPLIANT
        assert result.proof is not None
        assert result.counterexample is None

    def test_violating_model_returns_sat_with_counterexample(
        self, checker: Z3ComplianceChecker, violating_model_constraints: dict
    ) -> None:
        """SAT = violation found = model is NOT compliant — counterexample required"""
        result: GateResult = checker.check(
            model_constraints=violating_model_constraints,
            rule_id="RBI-MD-2022-§4.1.c",
        )
        assert result.status == ComplianceStatus.VIOLATION
        assert result.counterexample is not None
        assert "postal_code" in result.counterexample.variables
        assert result.proof is None

    def test_violation_report_contains_plain_english_explanation(
        self, checker: Z3ComplianceChecker, violating_model_constraints: dict
    ) -> None:
        """CO interface must never see raw Z3 output — AIRULES Rule 38"""
        result: GateResult = checker.check(
            model_constraints=violating_model_constraints,
            rule_id="RBI-MD-2022-§4.1.c",
        )
        assert result.plain_english_explanation is not None
        assert len(result.plain_english_explanation) > 20
        # Must not contain raw Z3 variable notation
        assert "x!" not in result.plain_english_explanation
        assert "!val!" not in result.plain_english_explanation

    def test_unknown_rule_id_raises_rule_not_found(
        self, checker: Z3ComplianceChecker, compliant_model_constraints: dict
    ) -> None:
        with pytest.raises(RuleNotFoundError):
            checker.check(
                model_constraints=compliant_model_constraints,
                rule_id="NONEXISTENT-RULE-999",
            )
```

### React unit test template (Vitest + Testing Library)

```typescript
// frontend/src/features/compliance-officer/components/ComplianceBadge.test.tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ComplianceBadge } from './ComplianceBadge'

describe('ComplianceBadge', () => {
  it('renders COMPLIANT with green styling and text label', () => {
    render(<ComplianceBadge status="compliant" />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveTextContent('Compliant')
    expect(badge).toHaveClass('badge-compliant')
  })

  it('renders VIOLATION with red styling, text label, and pulse animation', () => {
    render(<ComplianceBadge status="violation" />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveTextContent('Violation Detected')
    expect(badge).toHaveClass('badge-violation')
    // Dot must pulse on violation — DESIGN.md requirement
    const dot = badge.querySelector('.badge-dot')
    expect(dot).toHaveClass('animate-pulse')
  })

  it('never renders color without a text label — AIRULES Rule 37', () => {
    const statuses = ['compliant', 'violation', 'pending', 'running'] as const
    statuses.forEach(status => {
      const { unmount } = render(<ComplianceBadge status={status} />)
      // Color dot must always be accompanied by visible text
      expect(screen.getByRole('status')).not.toBeEmptyDOMElement()
      unmount()
    })
  })

  it('renders all 4 statuses without throwing', () => {
    const statuses = ['compliant', 'violation', 'pending', 'running'] as const
    statuses.forEach(status => {
      expect(() => render(<ComplianceBadge status={status} />)).not.toThrow()
    })
  })
})
```

---

## 4. Integration Tests

### What MUST have integration tests

| What | Why |
|------|-----|
| `POST /api/regulations` — full ingestion flow | Covers: LLM call → Z3 validation → Neo4j write → pending_approval state |
| `POST /api/regulations/{id}/approve` — approval state machine | Covers: state transition, auth check (CO role only), Neo4j update |
| `GET /api/certificates/{id}` — certificate retrieval + HMAC verify | Covers: Supabase read + HMAC re-verification (Rule 33 AIRULES) |
| `GET /api/pipeline/status` — live status reads | Covers: Supabase + Neo4j reads, correct serialization |
| Full CI gate sequence — `gate_runner.py` | Covers: all gates run in order, first failure halts correctly |
| Lineage write + query | Covers: Neo4j model↔regulation edge creation and traversal |
| Certificate immutability | Covers: second write attempt to same cert ID raises error |

### Test DB setup pattern

```python
# tests/conftest.py — shared fixtures for integration tests
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from src.api.main import app
from src.lib.supabase_client import get_supabase_client
from src.lib.neo4j_client import Neo4jClient


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_supabase():
    """Uses Supabase local emulator or a dedicated test project"""
    client = get_supabase_client(url=os.environ["SUPABASE_TEST_URL"])
    yield client
    # Cleanup: delete all rows created during tests
    await client.table("certificates").delete().neq("id", "00000000").execute()
    await client.table("pipeline_events").delete().neq("id", "00000000").execute()


@pytest.fixture(scope="session")
async def test_neo4j():
    """Uses a separate test Neo4j database"""
    client = Neo4jClient(uri=os.environ["NEO4J_TEST_URI"])
    yield client
    # Cleanup: wipe test regulation nodes
    await client.run("MATCH (n:TestRegulation) DETACH DELETE n")
    await client.close()


@pytest.fixture
async def client(test_supabase, test_neo4j) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def ml_engineer_token() -> str:
    """JWT for ml_engineer role — used in Authorization header"""
    return create_test_jwt(role="ml_engineer", user_id="test-mle-001")


@pytest.fixture
def compliance_officer_token() -> str:
    """JWT for compliance_officer role"""
    return create_test_jwt(role="compliance_officer", user_id="test-co-001")
```

### Integration test template

```python
# tests/integration/test_certificate_immutability.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_certificate_cannot_be_overwritten(
    client: AsyncClient,
    ml_engineer_token: str,
) -> None:
    """
    AIRULES Rule 4: Proof certificates are immutable once written.
    A second write attempt to the same model version must fail.
    """
    headers = {"Authorization": f"Bearer {ml_engineer_token}"}

    # First deployment — certificate created
    response = await client.post(
        "/api/pipeline/deploy",
        json={"model_version": "v2.1.4-test", "passed_gates": True},
        headers=headers,
    )
    assert response.status_code == 201
    cert_id = response.json()["certificate_id"]

    # Second deployment of SAME version — must fail
    response = await client.post(
        "/api/pipeline/deploy",
        json={"model_version": "v2.1.4-test", "passed_gates": True},
        headers=headers,
    )
    assert response.status_code == 409  # Conflict — cert already exists
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_certificate_hmac_tamper_detection(
    client: AsyncClient,
    ml_engineer_token: str,
    test_supabase,
) -> None:
    """
    AIRULES Rule 33: Tampered certificates must be detected and rejected.
    """
    headers = {"Authorization": f"Bearer {ml_engineer_token}"}

    # Create a real certificate
    deploy_resp = await client.post(
        "/api/pipeline/deploy",
        json={"model_version": "v-tamper-test", "passed_gates": True},
        headers=headers,
    )
    cert_id = deploy_resp.json()["certificate_id"]

    # Directly tamper with the proof_hash in Supabase
    await test_supabase.table("certificates").update(
        {"proof_hash": "tampered:sha256:00000000"}
    ).eq("id", cert_id).execute()

    # Retrieval must detect tampering and return 422
    response = await client.get(f"/api/certificates/{cert_id}", headers=headers)
    assert response.status_code == 422
    assert "tampered" in response.json()["detail"].lower()
```

---

## 5. E2E Tests

### Critical flows — must always have E2E coverage

These are the 3 flows that matter to an auditor, a compliance officer, and an ML engineer respectively:

| Flow | Why E2E | Actors |
|------|---------|--------|
| **Regulatory ingestion → human approval → rule active** | This is the human-in-the-loop gate. Must work end-to-end including the two-click approval UI | Compliance Officer |
| **Model submission → CI gate failure → violation report displayed** | The most important failure path. Blocked deployment must be visible, explainable, and undeniable | ML Engineer |
| **Successful deployment → proof certificate downloadable** | The legal output of Rego. Certificate must appear, be downloadable, and show correct model+regulation versions | Both |

### Playwright E2E template

```typescript
// tests/e2e/regulatory_ingestion_flow.spec.ts
import { test, expect, Page } from '@playwright/test'

test.describe('Regulatory ingestion → human approval flow', () => {

  test.beforeEach(async ({ page }) => {
    // Login as compliance officer
    await page.goto('/login')
    await page.fill('[data-testid="email"]', 'co@test.rego.dev')
    await page.fill('[data-testid="password"]', process.env.TEST_CO_PASSWORD!)
    await page.click('[data-testid="login-btn"]')
    await page.waitForURL('/compliance-officer/dashboard')
  })

  test('CO can upload regulation text and see LLM translation', async ({ page }) => {
    await page.goto('/compliance-officer/regulations/upload')

    // Drag-drop or paste regulatory text
    const dropzone = page.getByTestId('regulation-dropzone')
    await dropzone.fill(
      'The lending service provider shall not use geographic ' +
      'proxies such as postal codes in credit decision algorithms.'
    )

    await page.getByRole('button', { name: 'Extract Rules' }).click()

    // LLM translation appears (with loading state first)
    await expect(page.getByTestId('rule-translation-loading')).toBeVisible()
    await expect(page.getByTestId('rule-translation-card')).toBeVisible({
      timeout: 30_000  // LLM extraction can take up to 30s
    })

    // Translation shows a formal logic rule
    const ruleText = await page.getByTestId('rule-translation-text').textContent()
    expect(ruleText).toBeTruthy()
    expect(ruleText!.length).toBeGreaterThan(20)
  })

  test('CO approval requires two deliberate actions — AIRULES Rule 39', async ({ page }) => {
    await page.goto('/compliance-officer/approvals')

    // Find a pending rule
    const firstPendingRule = page.getByTestId('approval-row').first()
    await expect(firstPendingRule).toBeVisible()

    // Single click on Approve → confirmation step appears, rule NOT yet approved
    await firstPendingRule.getByRole('button', { name: 'Approve' }).click()
    await expect(page.getByTestId('approval-confirm-dialog')).toBeVisible()

    // Rule is still PENDING — one click is not enough
    const ruleId = await firstPendingRule.getByTestId('rule-id').textContent()
    const statusBefore = await firstPendingRule.getByRole('status').textContent()
    expect(statusBefore).toContain('Pending')

    // Second action — confirm in the dialog
    await page.getByRole('button', { name: 'Confirm Approval' }).click()

    // Now the rule is active
    await expect(firstPendingRule.getByRole('status')).toHaveText(/active/i)
  })

  test('Approved rule appears in active rules list with correct rule ID', async ({ page }) => {
    await page.goto('/compliance-officer/dashboard')
    await expect(page.getByTestId('active-rules-list')).toContainText('RBI-MD-2022')
  })
})
```

---

## 6. Manual Testing Checklist

Run this before every PR and every deploy. Check every box — do not skip.

### Core compliance flows
- [ ] Paste regulatory text → LLM extracts rules → rules appear in approval queue
- [ ] Approve a rule → rule moves to active state → appears in active rules list
- [ ] Reject a rule → rule moves to rejected state → does NOT appear in active rules
- [ ] Submit a non-compliant model → CI gates halt → violation report shows exact rule ID + plain English explanation
- [ ] Submit a compliant model → all CI gates pass → proof certificate generated
- [ ] Download proof certificate → file opens, shows model version + regulation version + Z3 hash
- [ ] Verify a certificate via `/api/certificates/{id}` → returns 200 with valid HMAC

### Auth and role enforcement
- [ ] Login as `compliance_officer` → routed to CO interface, not MLE interface
- [ ] Login as `ml_engineer` → routed to MLE interface, not CO interface
- [ ] CO cannot access `/ml-engineer/*` routes → redirected to CO dashboard
- [ ] MLE cannot call `POST /api/regulations/{id}/approve` → returns 403
- [ ] Unauthenticated request to any protected endpoint → returns 401
- [ ] Expired JWT → returns 401, frontend shows login screen

### Status display (AIRULES Rule 37 — color + text always together)
- [ ] Compliance badge on CO dashboard shows text label, not just a colored dot
- [ ] VIOLATION badge pulses (animate-pulse on dot)
- [ ] Pipeline gate rows show PASS/FAIL/RUNNING/QUEUED with both icon and label

### Edge cases
- [ ] Empty regulatory text field → submit button disabled or inline error shown
- [ ] LLM extraction times out → loading state cleared, error shown inline (not just toast)
- [ ] Z3 solver takes >2s → loading indicator visible, pipeline does not appear frozen
- [ ] Neo4j connection fails → FastAPI returns 503 with clear error, not 500

### Z3 smoke test
- [ ] `python scripts/verify_z3_install.py` exits 0 and prints Z3 version
- [ ] Z3 can prove a trivially compliant rule in < 100ms
- [ ] Z3 can produce a counterexample for a trivially violated rule

---

## 7. AI Testing Rules

### When AI MUST write tests — no exceptions

1. **Any function in `pipeline/ci/`, `pipeline/cd/`, `pipeline/ingestion/`** — these are the compliance core. Tests must include both COMPLIANT and VIOLATION cases.
2. **Any new FastAPI route** — must have an integration test covering auth, happy path, and 4xx error case.
3. **`ComplianceBadge` component** and any component that displays compliance status — must test all 4 statuses.
4. **Any state machine transition** (approval flow, pipeline stage transitions) — must test valid transitions AND invalid transitions (should raise error).
5. **Certificate generation and verification** — tests must include tamper detection case.
6. **Any bug fix** — write a regression test that reproduces the bug FIRST, then fix it.

### When AI MAY skip tests (with justification in PR comment)

- Pure Tailwind/layout components with no logic
- Pydantic models with no custom validators
- `__init__.py` re-export files
- Configuration files (`.env.example`, `pyproject.toml`)
- One-off seed scripts (test the seeded data, not the script)

### What AI must NEVER do

- Mark a compliance pipeline function as "done" without bilateral tests (COMPLIANT + VIOLATION)
- Mock the Z3 solver in unit tests — use real Z3 with simple test formulas instead
- Mock Neo4j for certificate lineage tests — use the test Neo4j instance
- Write a test that only checks the happy path for any gate in `pipeline/ci/`
- Write `assert True` or `pass` as test bodies as placeholders
- Skip the `test_tamper_detection` test because "it's unlikely" — it is required

### AI self-check before saying "done"

Before marking any task complete, run this checklist mentally:

```
□ Does every new function have a test?
□ For compliance functions: does the VIOLATION case have a test?
□ For state machines: do invalid transitions have tests?
□ Does the test use real Z3 / real DB (not mocked away)?
□ Do all tests pass locally (poetry run pytest)?
□ Does the CI gate pass (check GitHub Actions run)?
□ Is the test colocated in the right tests/ subfolder?
□ Does the test name describe the behavior, not the implementation?
  (test_compliant_model_returns_unsat ✓ / test_check_method ✗)
```

---

## 8. Test Commands

```bash
# ── PYTHON (run from project root) ──────────────────────────

# Run all Python tests
poetry run pytest

# Run unit tests only (faster — excludes integration)
poetry run pytest src/ -m "not integration"

# Run integration tests only
poetry run pytest tests/integration/ -m "integration"

# Run a specific test file
poetry run pytest src/pipeline/ci/tests/test_symbolic_check.py -v

# Run with coverage report
poetry run pytest --cov=src --cov-report=term-missing --cov-report=html

# Run Z3-specific tests only
poetry run pytest -k "z3 or symbolic or certificate" -v

# Run and stop on first failure (fast feedback during dev)
poetry run pytest -x

# ── TYPESCRIPT (run from frontend/) ─────────────────────────

# Run all frontend tests
npm run test

# Run in watch mode (during development)
npm run test:watch

# Run with coverage
npm run test:coverage

# Run a specific test file
npm run test ComplianceBadge.test.tsx

# ── E2E (run from project root) ──────────────────────────────

# Run all E2E tests (requires running backend + frontend)
npx playwright test

# Run a specific E2E file
npx playwright test tests/e2e/regulatory_ingestion_flow.spec.ts

# Run E2E with UI mode (headed, for debugging)
npx playwright test --ui

# ── COVERAGE TARGETS ─────────────────────────────────────────

# Minimum coverage thresholds (enforced in CI):
# pipeline/ci/         → 90%
# pipeline/cd/         → 90%
# pipeline/ingestion/  → 85%
# pipeline/ct/         → 80%
# lib/                 → 75%
# api/routes/          → 70% (integration tests cover the rest)
# frontend/features/   → 70%
```

---

## 9. CI Integration

| Trigger | Tests that run | Time budget | Fails PR if? |
|---------|---------------|------------|--------------|
| **Every PR** | Python unit tests + React unit tests + linting (ruff, mypy, eslint) + type check | < 5 min | Any test fails, any lint error, coverage below threshold |
| **Merge to main** | All of above + integration tests (test Supabase + test Neo4j) | < 10 min | Any integration test fails |
| **CT workflow trigger** (regulation drift detected) | Python unit tests + Z3 symbolic checks against new rule set | < 4 min | New rule causes existing compliant model to fail (triggers retraining) |
| **Pre-deploy (CD workflow)** | Full CI gate suite + certificate generation test + HMAC verification | < 3 min | Any gate fails — deployment blocked, AIRULES Rule 3 |
| **Weekly (scheduled)** | E2E tests against staging environment | < 15 min | Sends Slack/email alert (does not block — no live prod yet) |

### GitHub Actions workflow mapping

```yaml
# .github/workflows/ci.yml — runs on every PR
steps:
  - ruff check src/          # linting
  - mypy src/                # type checking
  - pytest src/ -m "not integration" --cov=src  # unit tests + coverage
  - npm run test:coverage    # frontend unit tests

# .github/workflows/integration.yml — runs on merge to main
steps:
  - pytest tests/integration/ -m "integration"   # needs TEST_SUPABASE_URL, NEO4J_TEST_URI

# .github/workflows/cd.yml — runs pre-deploy
steps:
  - pytest src/pipeline/ci/ src/pipeline/cd/ -v  # compliance gates
  - python scripts/verify_z3_install.py           # Z3 smoke test
  - pytest tests/integration/test_certificate_verify.py  # cert integrity
```

### Coverage enforcement (CI fails below these thresholds)

```ini
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-fail-under=80"

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

---

*TESTING.md is FINALIZED.*
*Every AI tool reads this before writing tests or calling anything "done".*
*In Rego: the VIOLATION test case is more important than the COMPLIANT test case.*
*A false COMPLIANT verdict is a bug with legal consequences.*
