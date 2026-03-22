# CONSTRAINTS.md — Project Constraints & Guardrails
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: FINALIZED
# ============================================================
# READ THIS BEFORE: suggesting any new service, installing
# any paid API, adding any infrastructure, or recommending
# anything that has a cost, complexity, or bundle size impact.
#
# Difference from AIRULES.md:
# AIRULES.md  → code quality and behavior rules
# CONSTRAINTS.md → budget, infrastructure, and complexity limits
#
# If it costs money, adds a service, increases bundle size,
# or needs a new env var — check this file first.
# ============================================================

## 1. Budget Constraints

**Monthly ceiling: $0.00**
This is a learning/portfolio project. Every service must run on its free tier.
The only permitted exception is OpenRouter API credits — free tier credits cover MVP usage.
Any suggestion that requires a credit card commitment requires explicit approval.

### Approved free-tier services

| Service | Free tier limit | What happens at limit | Action |
|---------|----------------|----------------------|--------|
| **Railway** | $5/month credit (hobby) | Deploy pauses | Switch to Render free tier (fallback) |
| **Render** | 750 hrs/month, sleeps after 15min inactivity | App cold-starts (~30s) | Acceptable for MVP demo; document in README |
| **Supabase** | 500MB DB, 2GB bandwidth, 50K MAU | API returns 429 | Reduce seed data, optimize queries |
| **Neo4j Aura Free** | 1 free instance, 200MB storage | Graph queries slow/fail | Prune old rule versions aggressively |
| **Kaggle Notebooks** | 30h GPU/week (P100), persistent storage | Weekly quota exhausted | Schedule CT runs — 1 retraining run uses ~5min, budget is generous |
| **HuggingFace Spaces** | ZeroGPU (A10G, free) for demo hosting | Rate limited on cold start | Use for live demo — ZeroGPU spins up in ~3s |
| **MLflow (local)** | Unlimited — runs locally in `./mlruns` | Disk space | Prune old runs via `mlflow gc` |
| **DVC (local/GitHub)** | GitHub repo storage limits (1GB soft) | Push fails | Use `.dvcignore` aggressively |
| **GitHub Actions** | 2,000 min/month (free tier) | Workflows queue/fail | Optimize CI to run only changed pipeline stages |
| **OpenRouter** | Free credits on signup (~$5 equivalent) | 429 rate limit | Switch to fallback model, reduce extraction calls |
| **Evidently AI** | Open source library — no API cost | — | No limit concern |
| **Z3 SMT Solver** | Open source — no API cost | — | No limit concern |

**GPU strategy — Kaggle for CT retraining:**
CT retraining (`pipeline/ct/trainer.py`) runs on Kaggle. The GitHub Actions CT workflow triggers a Kaggle notebook via the Kaggle API (`kaggle kernels push`). The retrained model artifact is saved to the Kaggle output, pulled back via `kaggle kernels output`, and registered in MLflow. This keeps GPU compute free and the orchestration in GitHub Actions where it's observable.

```
Kaggle CT flow:
GitHub Actions CT workflow
  → kaggle kernels push (triggers notebook with P100)
  → Notebook: load data, retrain XGBoost with constraint_loss
  → Notebook: save model.pkl to /kaggle/working/
  → GitHub Actions: kaggle kernels output → pull model.pkl
  → Register in MLflow → submit to CI gates
```

Setup required (one time):
- Create Kaggle account at kaggle.com
- Generate API key: Account → API → Create New Token → downloads kaggle.json
- Add to GitHub Actions secrets: KAGGLE_USERNAME and KAGGLE_KEY
- Add to local .env: KAGGLE_USERNAME=... and KAGGLE_KEY=...

### Requires explicit approval before adding (paid tier)

Any of the following requires updating this file AND getting confirmation before implementation:

- Railway Pro ($20/month) — only if free credit exhausted and demo is imminent
- Supabase Pro ($25/month) — only if storage genuinely exhausted
- OpenAI direct API (credit card required) — use OpenRouter instead
- Anthropic direct API (credit card required) — use OpenRouter instead
- Any cloud storage (S3, GCS, R2) — use local DVC + GitHub for MVP
- Any managed Kubernetes / container orchestration
- Any third-party monitoring SaaS (Datadog, Sentry paid)

### Off-limits entirely

| Service | Reason |
|---------|--------|
| AWS / GCP / Azure (paid services) | No cloud budget — free tiers only |
| Vercel (frontend hosting) | React served via Railway/Render with FastAPI — no separate Vercel deploy |
| PlanetScale / Neon / paid DB | Supabase free tier is sufficient |
| Redis / Upstash | GitHub Actions handles orchestration — no queue needed |
| Pinecone / Weaviate / vector DBs | Neo4j Aura handles knowledge graph — no vector DB needed |
| Auth0 / Clerk / paid auth | Supabase Auth is free and sufficient |
| Any LLM API requiring upfront payment | OpenRouter free credits only |

---

## 2. Infrastructure Constraints

### Deployment — Railway (primary) / Render (fallback)

| Constraint | Limit | Impact on Rego |
|-----------|-------|---------------|
| Memory per service | 512MB (Railway free) | Z3 solver is memory-efficient; PyTorch inference must use quantized model |
| CPU | Shared, burstable | Z3 proofs run fast (<500ms) — acceptable |
| Persistent disk | None on free tier | MLflow runs stored in GitHub artifacts, not Railway disk |
| Concurrent connections | ~10 (free tier) | MVP demo traffic only — acceptable |
| Build timeout | 10 minutes | Keep Docker image lean; use multi-stage build |
| Cold start (Render) | ~30 seconds after 15min sleep | Document in README; acceptable for demo |
| Egress bandwidth | 100GB/month (Railway) | Neo4j + Supabase calls are small payloads — no risk |

### Database — Supabase Free Tier

| Constraint | Limit |
|-----------|-------|
| Database size | 500MB |
| Bandwidth | 2GB/month |
| Max connections | 60 direct / 200 via pooler |
| Row limit | No hard limit (within 500MB) |
| Edge Functions | 500K invocations/month |
| Storage | 1GB |

**Implication for Rego:** Certificate records and pipeline events are small JSON rows. 500MB is sufficient for hundreds of thousands of records. Risk: large regulatory document blobs stored as text — store document metadata only, not full text, in Supabase. Full text goes to DVC/GitHub.

### 4.4 Data Privacy (PII)
- [ ] Audit all `logger.*` calls in `src/` — confirm no applicant PII fields logged
- [ ] Audit `pipeline_events` table — confirm no individual applicant data stored (model-level only)
- [ ] Verify loan approval training data is anonymized before use (hashed IDs only)
- [ ] Loan training data must be fully anonymized before use — use hashed applicant IDs only. Original PII never enters the codebase.

### Knowledge Graph — Neo4j Aura Free

| Constraint | Limit |
|-----------|-------|
| Storage | 200MB |
| Nodes | No hard cap (within 200MB) |
| Concurrent connections | 1 (free tier) |
| Instance count | 1 |

**Implication for Rego:** One Neo4j instance. Connection pooling is critical — use the Neo4j Python driver's built-in connection pool. Lineage graph must be pruned: keep the last 10 model versions per regulation. Archive older lineage to Supabase JSON column.

### GitHub Actions Free Tier

| Constraint | Limit |
|-----------|-------|
| Minutes/month | 2,000 |
| Storage for artifacts | 500MB |
| Concurrent jobs | 20 |
| Job timeout | 6 hours |

**Implication for Rego:** CI pipeline (Z3 checks + tests) must complete in under 10 minutes. CT retraining workflow must complete in under 30 minutes. If minutes are running low: cache Poetry dependencies and npm modules aggressively between runs.

**GitHub Actions minute estimate per pipeline run:**
- CI gates: ~4 min (Z3 checks + pytest + fairness)
- CT retraining: ~20 min (PyTorch fine-tune on small model)
- CD deploy: ~3 min
- Total per full pipeline run: ~27 min
- Budget allows ~74 full pipeline runs/month — sufficient for MVP

---

## 3. Performance Constraints

### API Response Times

| Endpoint | Target | Hard limit | Notes |
|----------|--------|-----------|-------|
| `GET /health` | <50ms | 200ms | Z3 smoke test included |
| `GET /pipeline/status` | <200ms | 500ms | Reads Supabase only |
| `POST /regulations` (ingestion submit) | <500ms | 2s | Async — LLM runs in background |
| `GET /certificates/{id}` | <300ms | 1s | Includes HMAC verify |
| Z3 symbolic check (per rule) | <500ms | 2s | 12 rules = <6s total |
| Full CI pipeline | <10 min | 15 min | GitHub Actions wall clock |
| Law → compliant deployment | <3 min | 5 min | PRD success metric |

### Frontend Bundle Size

| Target | Hard limit |
|--------|-----------|
| Initial JS bundle | <250KB gzipped | 400KB |
| Per-route chunk | <100KB gzipped | 150KB |
| Total assets | <1MB | 2MB |

**Enforced by:** Vite bundle analyzer in CI. Build fails if initial bundle exceeds 400KB gzipped.

**Risk areas:**
- `recharts` (~80KB) — use only on MLE dashboard, lazy-loaded
- `@tanstack/react-query` (~13KB) — acceptable
- Neo4j browser driver — do not import in frontend; all graph queries go through FastAPI

### Lighthouse Scores (CO interface — institutional trust matters)

| Metric | Target |
|--------|--------|
| Performance | ≥85 |
| Accessibility | ≥95 (WCAG AA — legal compliance tool) |
| Best Practices | ≥90 |
| SEO | Not applicable (auth-gated tool) |

---

## 4. Complexity Constraints

**The single most important complexity rule for Rego:**
> This is a learning project with a $0 budget. Every complexity decision must answer: "Can a solo developer understand and debug this at 2am?" If the answer is no — it's too complex.

**Hard complexity limits:**

| What | Constraint | Why |
|------|-----------|-----|
| Microservices | ❌ Forbidden — monorepo only | One Railway/Render deployment, not 5 |
| Background job queues (Celery, Redis, BullMQ) | ❌ Forbidden | GitHub Actions handles all async orchestration |
| Event streaming (Kafka, Kinesis) | ❌ Forbidden | WebSocket + Supabase realtime is sufficient |
| Container orchestration (K8s, ECS) | ❌ Forbidden | Single Docker container on Railway |
| Separate frontend hosting (Vercel) | ❌ Forbidden | React served by FastAPI static files or same Railway service |
| Multiple databases of the same type | ❌ Forbidden | One Supabase instance, one Neo4j instance |
| Custom auth implementation | ❌ Forbidden | Supabase Auth only |
| More than 1 LLM provider | ⚠️ Via OpenRouter only | OpenRouter abstracts provider — do not call multiple providers directly |
| New pipeline stage beyond ingestion/ci/ct/cd | ⚠️ Requires PRD update | Pipeline stages are locked in PRD.md |

**Complexity gate — ask before adding:**
- Any new external service (even free tier)
- Any new environment variable
- Any new database table that wasn't in the original schema
- Any new GitHub Actions workflow
- Any npm or pip package not in TECH.md

---

## 5. API & Rate Limit Awareness

| API / Service | Free tier limit | At-limit behavior | Fallback |
|--------------|----------------|-------------------|---------|
| **OpenRouter** | ~$5 free credits | 429 Too Many Requests | Switch `LLM_DEFAULT_MODEL` to `mistralai/mistral-7b-instruct` (free on OpenRouter) |
| **OpenRouter rate limit** | 20 req/min (free) | 429, automatic retry | Exponential backoff in `lib/llm_client.py` — max 3 retries |
| **Supabase REST API** | 500MB DB, 2GB bandwidth | 503 on bandwidth exceeded | Reduce payload size; add response caching |
| **Supabase Auth** | 50,000 MAU | Auth fails for new users | Not a concern for MVP (< 5 users) |
| **Neo4j Aura** | 200MB, 1 connection | Slow queries / connection errors | Connection pool max_size=1; queue requests |
| **HuggingFace Inference API** | Rate limited (free tier) | 503 | Use local PyTorch inference for MVP; HF for model download only |
| **GitHub Actions** | 2,000 min/month | Workflows queue indefinitely | Optimize: skip CT workflow if regulation hash unchanged |
| **Railway** | $5 credit/month | Service paused | Migrate to Render (same Docker image, same env vars) |
| **Z3 SMT Solver** | Local library — unlimited | OOM if formula too large | Formula size validation in `ingestion/validator.py` before Z3 call |

### LLM cost estimate for MVP

```
Regulatory text ingestion: ~2,000 tokens input + ~500 tokens output per rule
RBI Master Directions 2022 has ~50 extractable rules
Initial seed: 50 rules × 2,500 tokens = 125,000 tokens
Claude 3.5 Sonnet via OpenRouter: ~$0.003 per 1K tokens = ~$0.375 total
Free credits cover this comfortably.

Ongoing: Each new regulation update = ~5 rules = ~12,500 tokens = ~$0.04
Monthly ongoing cost (10 regulation updates): ~$0.40
Well within free credit buffer.
```

---

## 6. Approved vs Requires Approval

| ✅ Can add without asking | ⚠️ Requires approval — update CONSTRAINTS.md first |
|--------------------------|---------------------------------------------------|
| New pytest test file | Any new external service (even free tier) |
| New Pydantic schema | Any new npm or pip package |
| New FastAPI route (no new service) | New GitHub Actions workflow |
| New React component (no new library) | New environment variable |
| New Z3 rule in test fixtures | New database table |
| Refactoring existing code | New Neo4j node/relationship type |
| Updating `.env.example` | Changing Railway/Render configuration |
| Adding structured logging | Any paid API integration |
| Bug fixes | New pipeline stage |
| Documentation updates | Changing the proof certificate schema |
| New seed script | Upgrading pinned package versions |

**What "approval" means on this project:**
Update this file with the proposed addition, the reason, and the cost/complexity impact. Then proceed. There is no other person to ask — this is a solo project. The approval gate exists to force a moment of deliberate thought before adding complexity.

---

## 7. The Escalation Rule

When an action would hit a constraint, AI must respond with this exact format before proceeding:

```
⚠️ CONSTRAINT: [proposed action] would [cost/complexity/limit implication].

This exceeds: [specific constraint from this document — section + line].

Constrained alternative: [what can be done within limits].

Options:
  (1) Proceed with constrained alternative → [describe]
  (2) Update CONSTRAINTS.md to explicitly approve this → [describe what needs to change]
  (3) Defer to v2 → [note it in ISSUES.md as a known limitation]

Which do you prefer?
```

### Example escalation — correct behavior

```
⚠️ CONSTRAINT: Adding Sentry for error monitoring would require a paid plan
for >5K errors/month and adds a new external service.

This exceeds: Section 4 — "Any new external service requires approval."

Constrained alternative: Use Railway's built-in log viewer + structlog 
JSON output piped to a local file. Free, zero new services, sufficient for MVP.

Options:
  (1) Proceed with structlog + Railway logs (constrained) → implement now
  (2) Update CONSTRAINTS.md to approve Sentry free tier → update doc first
  (3) Defer Sentry to v2 → note in ISSUES.md

Which do you prefer?
```

### What AI must NEVER do when hitting a constraint

- Silently add a paid service and mention it in a comment
- Say "I'll just use X for now, we can change it later" without flagging
- Install a package from outside TECH.md without the escalation prompt
- Assume that "flexible budget" means unlimited — budget is $0

---

*CONSTRAINTS.md is FINALIZED.*
*Every constraint here is binding until this file is explicitly updated.*
*When in doubt: do less, not more. This is a $0 learning project — complexity is the enemy.*
