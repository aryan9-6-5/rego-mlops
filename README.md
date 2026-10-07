# Rego

Continuous regulatory compliance reasoning for machine learning.

Most MLOps platforms retrain a model when the data changes. Rego treats a change in the law as the trigger instead. A regulation is translated into formal logic, a person approves that translation, and every model must then be proved compliant with it before it can be deployed. The proof is stored as a signed certificate that an auditor can check in seconds.

The first use case is loan approval models under the Reserve Bank of India (RBI) Digital Lending Directions, 2025.

## What Rego does differently

| Common practice | Rego |
|:---|:---|
| Retraining is triggered by data drift | Retraining is triggered by regulatory drift |
| Compliance is checked after deployment | Compliance is a gate: a non-compliant model cannot be deployed |
| Engineers interpret the law by hand | An LLM drafts a candidate rule, Z3 checks its structure, and a compliance officer approves its meaning |
| An audit is a long report | An audit is a certificate that can be machine-verified |
| Model versions are tracked | Law versions and model versions are tracked together |
| The compliance team is outside the pipeline | The compliance officer is a step in the pipeline |

## Status

All seven features in the plan are implemented and tested: ingestion, version control and lineage, compliance CI gates, regulation-triggered training, gated deployment, proof certificates, and the two dashboards.

What has been verified:

- The Python test suite (more than 450 tests, 98 percent coverage), the frontend unit tests, and seven browser tests run in CI on every push.
- The API, the Z3 checks, the approval and deployment flows, and the certificate signing run end to end against in-memory stand-ins for the outside services.
- The production container configuration runs and serves both the API and the web app.

What has not been verified against real services yet:

- Neo4j queries, Supabase row level security and Realtime, Railway deployment, Kaggle training, GitHub workflow dispatch, and a real LLM. The tests use stand-ins for these.
- A live deployment. See `docs/DEPLOY.md`.

Known limitations are listed at the end of this file.

## How it works

Three roles use the system:

- Compliance officer: pastes regulatory text, reviews the rule the system extracted, and approves or rejects it. Sees plain English only.
- ML engineer: submits models, reads violation reports (including the solver's counterexample), and deploys.
- CTO: read-only access to everything.

The flow:

1. The compliance officer pastes a provision of the regulation.
2. An LLM drafts a candidate rule in SMT-LIB2, a standard logic format. The LLM output is never trusted as a final rule.
3. Z3 checks that the rule is well formed, not always true, not always false, and not self-contradictory. A rule that fails is rejected before a person sees it.
4. The compliance officer reads the original text beside a plain-English meaning and the exact condition in words, then approves in two deliberate steps.
5. The approved rule is stored in the Neo4j knowledge graph as a versioned regulation. A newer version supersedes the older one and the older one is kept.
6. When a model is submitted, four gates run in order: a symbolic check with Z3, a boundary robustness check, a fairness check, and a performance regression check. The first failure stops the run and later gates do not execute.
7. To deploy, Rego confirms that every gate passed, proves the model against the rules active at that moment, writes one signed certificate, records which regulation versions the model was certified against, runs a canary with a second Z3 check, and promotes.
8. A new active regulation version is detected by a scheduled GitHub Actions workflow, which retrains the model on Kaggle and submits it to the same gates.

## Architecture

```
  Browser (React, two interfaces)
        |
        |  HTTPS, /api
        v
  FastAPI ------------------------------+
   |         |          |               |
   |         |          |               +--> OpenRouter (LLM, offline only)
   v         v          v
 Supabase   Neo4j     Z3 solver
 (users,    (rule     (the only engine
 events,    versions, allowed to decide
 certs)     lineage)  compliance)

  GitHub Actions
   - ci.yml : lint, types, tests, security, browser tests
   - ct.yml : detect regulation change, retrain on Kaggle, run gates
   - cd.yml : placeholder, real deploys go through the API

  Railway: one container serving the API and the built web app
```

The code is organised in three layers. `lib` holds clients for outside services and imports nothing else in the project. `pipeline` holds the ingestion, ci, ct and cd stages and does not import from `features`. `features` holds dashboard-facing logic. The rules are enforced by tests and linting.

## Try it in five minutes, with no accounts

This runs the real API and the real Z3 solver. Neo4j, Supabase, Railway and the LLM are replaced by in-memory stand-ins, so nothing needs to be installed or configured beyond Python.

```bash
git clone https://github.com/aryan9-6-5/rego-mlops.git
cd rego-mlops
pip install poetry
poetry install
poetry run python scripts/demo_offline.py
```

The script walks through ingesting three real RBI provisions, approving them, passing a compliant model through the gates and deploying it, blocking a model that reads the phone contact list, checking a certificate as an auditor, and detecting a tampered certificate. It finishes in about a second.

To run the tests:

```bash
poetry run pytest --cov            # Python, with the 90 percent coverage gate
cd frontend
npm ci
npm test                           # component and unit tests
npx playwright test                # browser tests, using the Chrome on your machine
```

## Full setup

You need Python 3.11 or newer, Node 22, Poetry 2, Docker (for Neo4j), a Supabase project, and an OpenRouter API key.

1. Configure the environment.

   ```bash
   cp .env.example .env
   ```

   Fill in the values. Use the same `NEO4J_PASSWORD` for the Neo4j container and the backend (it defaults to `password` for local use). `PROOF_CERT_SECRET` must be at least 32 random bytes, for example the output of `python -c "import secrets; print(secrets.token_urlsafe(48))"`. The Supabase service key stays on the server and must never be placed in a `VITE_` variable.

2. Create the database. Run the files in `supabase/migrations/` in order, 01 to 09, in the Supabase SQL editor or with the Supabase CLI. Migration 08 tightens row level security and makes certificates append-only. Migration 09 creates the private Storage bucket that holds model files and records which files each CI result was about.

3. Start Neo4j and the backend.

   ```bash
   docker compose up -d neo4j
   poetry install
   poetry run python scripts/verify_z3_install.py
   poetry run uvicorn src.api.main:app --reload --port 8000
   ```

4. Start the frontend.

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

   The app is at http://localhost:5173 and the API documentation at http://localhost:8000/docs.

5. Create users. Each person needs a Supabase Auth account and a row in the `users` table with a role of `compliance_officer`, `ml_engineer` or `cto`. For two demo accounts, run `poetry run python scripts/create_demo_users.py`.

6. Create sample models: `poetry run python scripts/make_demo_models.py`.

## The Z3 approach

A language model can draft a rule but cannot be trusted to decide whether a model complies. Rego therefore uses an SMT solver, Z3 from Microsoft Research, for every compliance decision. SMT solvers are used in practice to check device drivers, cloud access policies and hardware designs.

A rule states the condition a compliant model must meet, for example that the weight of a prohibited feature is exactly zero. A model is described by the weight it gives each feature. Z3 searches for a way the rule could be false given those weights:

- If no such way exists (unsatisfiable), the model is proved compliant.
- If one exists (satisfiable), Z3 returns a counterexample, and the report names the rule and the features involved.
- If Z3 cannot decide, the result is treated as not compliant. Every gate fails closed.

The LLM is only ever used offline to draft a rule. It is never used inside a gate or a deployment decision. A person approves the meaning of each rule before it takes effect.

## Adding a rule

1. Sign in as a compliance officer and open Add Regulation.
2. Enter the section (letters, digits and . ( ) _ - only) and paste the text of the provision.
3. Wait for extraction, usually 10 to 30 seconds, then open the approval queue.
4. Compare the source text with the plain-English meaning and the exact condition shown in words.
5. Approve by choosing Yes, typing ACTIVATE, and confirming. Rejecting also takes two steps.

A rule the validator rejects appears under Could not be verified with a plain-English reason.

## Submitting a model

A model is a folder of two files, called a bundle. Locally the folder sits inside `MODEL_ARTIFACT_DIR`. In production bundles are kept in a private Supabase Storage bucket, `model-bundles`, as `<model name>/profile.json` and `<model name>/evaluation.json`. `MODEL_BUNDLE_STORE` selects `local` (the default for development) or `supabase` (the default in the production image).

`profile.json` lists the weight of each feature, named `<feature>_weight`:

```json
{"weights": {"age_weight": 0.2, "income_weight": 0.4, "contact_list_weight": 0.0}}
```

A feature that is not listed counts as weight zero.

`evaluation.json` holds held-out predictions used by the fairness and regression gates:

```json
{"y_true": [1, 0], "y_pred": [1, 0], "baseline_y_pred": [1, 0], "groups": ["a", "b"]}
```

To put bundles in storage, run `poetry run python scripts/make_demo_models.py --upload` for the sample bundles. Bundles produced by the training workflow are uploaded automatically. Uploading a bundle again replaces it.

As an ML engineer, open Pipeline Monitor, enter the bundle name, and choose Run compliance gates. When all four gates are compliant, a Deploy button appears.

Each CI result records a SHA-256 hash of the exact files it checked. A deploy is refused unless every gate passed on the files being deployed, so replacing a bundle after it passed means the checks must run again.

## Proof certificates

A certificate records the model version, every regulation version it was certified against, and a proof hash. The hash is a SHA-256 over the model files and, for each active rule, its version and a hash of its formula. The same model checked against the same rules always gives the same hash, so deploying it twice is refused with a 409. A new regulation version gives a new hash and so a new certificate.

Each certificate is signed with HMAC-SHA256 over its id, model version, regulation versions and proof hash, using `PROOF_CERT_SECRET`. The signature is checked on every read. A certificate that fails the check is never served: the API returns 422 and the list marks it as failed. There is no route to create, change or delete a certificate, and the database refuses updates and deletes.

An auditor needs no account. To check a hash:

```bash
curl -X POST https://YOUR-HOST/api/certificates/verify \
  -H "Content-Type: application/json" \
  -d '{"cert_id": "<certificate id>", "proof_hash": "<hash from the downloaded file>"}'
```

The reply is `{"valid": true, ...}` or `{"valid": false, "explanation": "..."}`. This route is limited to 30 requests a minute per client address.

The compliance officer's screen does not display the hash. They can copy it with Copy hash, and the downloaded JSON file contains it.

## API summary

All routes are under `/api`, except the health checks, which are also at `/health/`.

| Route | Roles |
|:---|:---|
| `POST /regulations/`, `POST /regulations/{id}/approve`, `POST /regulations/{id}/reject` | compliance officer |
| `GET /regulations/`, `GET /regulations/jobs/{id}` | compliance officer, CTO |
| `POST /pipeline/submit`, `POST /pipeline/deploy`, `POST /pipeline/trigger-ct` | ML engineer |
| `GET /pipeline/status`, `GET /pipeline/drift-log`, `GET /models/diff`, WebSocket `/pipeline/events` | ML engineer, CTO |
| `GET /models/`, `GET /models/{version}/lineage`, `GET /certificates/`, `GET /certificates/{id}` | all roles |
| `POST /certificates/verify`, `GET /health/`, `GET /health/z3` | public |

## GitHub Actions workflows

| Workflow | Trigger | What it does |
|:---|:---|:---|
| `ci.yml` | every push and pull request to main | Jobs: Python lint (ruff) and types (mypy); Python tests with a 90 percent coverage gate; frontend lint and unit tests; browser tests; security (bandit, a dependency audit of `poetry.lock`, and `npm audit`) |
| `cd.yml` | after CI succeeds on main | Placeholder. Deployment happens through the API, not this workflow |
| `ct.yml` | manually with a regulation version (the 5 minute schedule is paused until the secrets are set) | Detects a new active regulation version, retrains on Kaggle with the prohibited features excluded, logs to MLflow, then runs the CI gates and fails if any gate fails |

## Security

- Every route requires a login except the health checks and certificate verification. A missing or invalid token is always the same 401 with no detail.
- Roles are enforced in the API, not only in the interface. A test lists every route with its allowed roles and fails if a route is added without an entry.
- Regulatory text is stripped of HTML and control characters and limited to 50,000 characters before it can reach the LLM.
- The service key never leaves the backend. Row level security gives anonymous users no access and signed-in users read-only access. The model file bucket is private with no policies, so only the backend can read or write it.
- The compliance officer interface never shows rule identifiers, proof hashes or solver output.

## Project structure

```
src/api/            FastAPI application, routes, schemas, rate limiting, static file serving
src/lib/            clients for Z3, the LLM, Neo4j, Supabase and MLflow, and the model file loader
src/pipeline/       ingestion, ci (gates), ct (retraining), cd (certificates and deployment)
src/features/       logic used by the dashboards, such as the model diff
frontend/           React and TypeScript application, unit tests, and browser tests
supabase/           database migrations
notebooks/          the Kaggle retraining notebook
scripts/            demo, seeding, audit and install-check scripts
tests/integration/  end-to-end API tests and a stateful in-memory test environment
docs/               project documents
```

## Documentation

- `docs/DEPLOY.md`: deploying to Railway, with a checklist.
- `docs/DEMO.md`: demo script, sample rules and accounts.
- `docs/TECH.md`: stack, conventions and decisions.
- `docs/TESTING.md`: test strategy and the status of the manual checklist.

## Known limitations

- The sample rules (`scripts/rbi_digital_lending_2025.py`) are three real provisions of the RBI Digital Lending Directions, 2025, but turning a provision into a condition on model weights is an interpretation. Paragraph 7(i) is the least literal. Rules in the test suite use invented names such as a PIN code feature as plain test data and are not claims about RBI rules.
- Railway cannot split traffic by percentage. The canary deploys to a separate service that receives no live traffic.
- Re-deploying a model that was already certified against the same rules is refused. A rollback path with its own certificate is not built.
- The confidence score described in the design documents is not implemented. Reviewers rely on the plain-English meaning and the exact condition.
- Fairness and regression gates use simple pure-Python metrics, not Evidently. Neither Evidently nor a training dataset is included, so the Kaggle notebook needs a dataset you provide.
- Frontend build tools (Vite, Vitest, Tailwind) have known advisories that need major version upgrades. None of them is shipped to the browser.

## License

MIT. See `LICENSE`.
