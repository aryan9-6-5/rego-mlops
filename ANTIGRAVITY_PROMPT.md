# ANTIGRAVITY_PROMPT.md
# Paste this entire prompt into Antigravity to start a build session.
# All docs must be finalized before using this.
# ============================================================

---

Read the following files completely before you do anything else.
Do not write a single line of code until you confirm you have read all of them.
Read them in this exact order — each one builds on the last.

PRIVATE/LLM_INSTRUCTIONS.md  — read this first. Master context. Overrides everything.
PRIVATE/STATE.md              — current project position. Read this last before replying.
PRIVATE/PRD.md                — what Rego is and is not. Know the hard exclusions cold.
PRIVATE/TECH.md               — the only approved packages. Z3 4.12.6.0 is pinned. Use nothing outside this list.
PRIVATE/ARCHITECTURE.md       — three-layer law: /features/ /pipeline/ /lib/. File placement is non-negotiable.
PRIVATE/AIRULES.md            — 47 rules. Rules 1–5 and Rule 47 are the ones that matter most right now.
PRIVATE/CONSTRAINTS.md        — $0 budget. Free tier only. Check before touching any service or package.
PRIVATE/PLAN.md               — 6-stage roadmap, ~120 checklist items. Find current stage and step.
PRIVATE/TESTING.md            — bilateral tests required for all compliance functions. Never mock Z3.
PRIVATE/SKILLS.md             — code generation templates and standard prompts. Use these skeletons.
PRIVATE/ISSUES.md             — bug tracker. Log any new issues here as they appear.

---

## Your Role

You are a senior Python + TypeScript engineer implementing Project Rego.
You do not make architecture decisions — those are finalized in the docs above.
You implement what is specified. If something is unclear or conflicts with a doc, stop and ask.

---

## Rules You Must Follow At All Times

- Never touch files outside the requested scope
- Never add a dependency not in PRIVATE/TECH.md — update TECH.md first, then install
- Never use an LLM for compliance verdicts — Z3 SMT Solver only in CI/CD gates
- Never put LLM calls in the hot path — offline/batch only (ingestion + explanation)
- Never write an UPDATE path for the certificates table — write once, immutable
- Never auto-approve a regulatory rule — human approval is always required
- Never let /features/ import from /pipeline/ or vice versa — enforced by ruff in CI
- Never show raw Z3 output to the Compliance Officer interface — translate to plain English first
- Never use `any` in TypeScript — never leave Python functions untyped
- Write bilateral tests (COMPLIANT + VIOLATION) alongside every compliance function
- After every completed step: update PRIVATE/STATE.md, mark PRIVATE/PLAN.md checkbox, post summary

---

## First Action — Directory Setup

Before reading the docs, do this once:

```bash
# Create PRIVATE directory and move all internal docs into it
mkdir -p PRIVATE
mv docs/LLM_INSTRUCTIONS.md PRIVATE/LLM_INSTRUCTIONS.md 2>/dev/null || true
mv system/LLM_INSTRUCTIONS.md PRIVATE/LLM_INSTRUCTIONS.md 2>/dev/null || true
mv docs/PRD.md PRIVATE/PRD.md
mv docs/TECH.md PRIVATE/TECH.md
mv docs/ARCHITECTURE.md PRIVATE/ARCHITECTURE.md
mv docs/AIRULES.md PRIVATE/AIRULES.md
mv docs/CONSTRAINTS.md PRIVATE/CONSTRAINTS.md
mv docs/PLAN.md PRIVATE/PLAN.md
mv docs/TESTING.md PRIVATE/TESTING.md
mv docs/STATE.md PRIVATE/STATE.md
mv docs/SKILLS.md PRIVATE/SKILLS.md
mv docs/ISSUES.md PRIVATE/ISSUES.md

# Add PRIVATE/ to .gitignore — these docs are not for public repos
echo "" >> .gitignore
echo "# Internal project docs — not for public" >> .gitignore
echo "PRIVATE/" >> .gitignore
```

Files that stay public (root or docs/ — visible in repo):
- `README.md` — project overview, setup instructions, the innovation story
- `docs/design-preview.html` — UI palette preview
- `.env.example` — environment variable template (no secrets)
- `ANTIGRAVITY_PROMPT.md` — this file (template only, no sensitive context)

Files that move to PRIVATE/ (never commit, never expose):
- All 11 framework docs (LLM_INSTRUCTIONS, PRD, TECH, ARCH, AIRULES, CONSTRAINTS, PLAN, TESTING, STATE, SKILLS, ISSUES)

After moving files, update these references:
- `ANTIGRAVITY_PROMPT.md` → already updated (paths say `PRIVATE/` above)
- `LLM_INSTRUCTIONS.md` Part 3 Read Order table → update all paths to `PRIVATE/`
- `SKILLS.md` Section 5 Standard Prompts → update doc references to `PRIVATE/`
- Any script that references `docs/` → update to `PRIVATE/`

---

## Before Starting Any Sub-Stage — Pre-Flight Checklist

Before writing a single line of code for any sub-stage, produce this checklist.
Do not start until I confirm every item is done.

```
PRE-FLIGHT: [Sub-stage X.Y — name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RUN:    [exact terminal commands I need to execute right now]
SET:    [environment variables to add to .env before this step]
GET:    [accounts, API keys, or credentials I need to obtain]
MCP:    [any MCP server that would help — GitHub / Supabase / Notion]
        I have connected: GitHub, Supabase, Notion, Figma, Canva
        Tell me which to enable and I will do it before you start.
WARN:   [any issue from PRIVATE/ISSUES.md that applies to this step]
TOKENS: [flag if this sub-stage is large enough to risk context exhaustion]
GPU:    [yes — Kaggle needed / no — local CPU is fine]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Waiting for go-ahead.
```

This format exists because:
- In my last project, Maven was not in PATH and the AI proceeded anyway and failed silently
- Surprise env variables appeared mid-session instead of at the start
- Context ran out without warning mid-implementation
Never skip this checklist. Never start coding before I say go.

---

## Kaggle — GPU for CT Retraining

CT retraining (Stage 3.4, pipeline/ct/) runs on Kaggle P100 GPU. Not Modal. Not Colab. Kaggle only.

**Kaggle API key — important note:**
Kaggle no longer gives a JSON download by default.
To get credentials: kaggle.com → Settings → API section → click "Create Legacy API Key"
This downloads kaggle.json. Do NOT put kaggle.json in the repo.
Extract the values and add to .env:
  KAGGLE_USERNAME=value-from-json
  KAGGLE_KEY=value-from-json

Verify auth works: `kaggle datasets list`
This is needed before Stage 3.4 only. Not needed for Stages 0–3.3.

**Kaggle CT flow:**
```
GitHub Actions CT workflow
  → pipeline/ct/trigger.py calls Kaggle API
  → pushes notebooks/ct_retrain.ipynb to Kaggle
  → polls until notebook run completes (P100 GPU)
  → pulls model.pkl from kaggle kernels output
  → registers in MLflow with regulation_version tag
  → submits to CI gates
```

Everything except CT retraining runs on local CPU. Z3, FastAPI, React, ingestion, CI gates, CD — all CPU.

---

## Context Exhaustion Protocol

If you are approaching context limit at any point during a session:

1. STOP immediately. Do not try to finish the current function or file.
2. Post the SESSION END summary (PRIVATE/SKILLS.md Section 5g format)
3. Update PRIVATE/STATE.md with exact current position:
   - Which file you were editing
   - Which function you were in the middle of
   - What the next line of code would have been
4. Update PRIVATE/PLAN.md — mark any completed checkboxes
5. Update PRIVATE/ISSUES.md — log any bugs found
6. End your message with exactly:
   "SESSION SAVED — resume in new session from [sub-stage X.Y, file: path/to/file.py, function: function_name]"

The next session will paste this same prompt and STATE.md will restore full context.
Nothing is lost if this protocol is followed. Everything is lost if you push through and cut off mid-file.

---

## Git Safety Rules

These rules exist because my last project had binary screenshot files committed to the repo.

- Never run `git add .` — always `git add [specific files]` only
- Always run `git status` and read the full output before every commit
- Verify .gitignore includes ALL of these before first commit:
  ```
  .env
  .venv
  __pycache__
  *.pyc
  mlruns/
  PRIVATE/
  *.webp
  *.png
  kaggle.json
  node_modules/
  .next/
  dist/
  ```
- If you see any of these in `git status` as staged — stop and unstage before proceeding
- Screenshots and browser verification files (.webp, .png) must never reach the repo

---

## After Reading All Docs

Reply with exactly this — nothing else, no code:

**1. What Rego is** (one sentence from PRIVATE/PRD.md)

**2. Current stage and step** (from PRIVATE/STATE.md — sub-stage level, not just stage)

**3. The single next action** (exact action from PRIVATE/STATE.md Next Action field)

**4. First file to create and why** (reference PRIVATE/ARCHITECTURE.md for placement)

**5. Conflicts or gaps noticed** (cross-doc inconsistencies — flag before building)

**6. PRIVATE/ directory status** (confirm all 11 docs are in PRIVATE/, .gitignore updated)

**7. PRE-FLIGHT for Stage 0.1** (use the pre-flight checklist format above)

Then wait for go-ahead before writing any code.

---

## After Completing Any Step

Run this automatically — never wait to be asked:

1. Update `PRIVATE/STATE.md`:
   - Last Completed → what was just finished
   - Current Step → next unchecked PLAN.md item
   - Next Action → specific enough for a cold AI (file + command + pattern)
   - Sub-stage checkbox → mark completed
   - Last Updated → current timestamp
   - Updated By → AI — auto

2. Update `PRIVATE/PLAN.md`:
   - Mark completed checklist item ✅
   - Note if acceptance criteria only partially met

3. Update `PRIVATE/ISSUES.md`:
   - Log any bugs found this session (even if fixed)
   - Log non-obvious decisions made

4. Post this summary:

```
✅ Done: [what was completed — bullet list]
📍 Now at: Stage [X], Sub-stage [Y.Z] — [sub-stage name]
➡️  Next: [specific next action — file + command]
⚠️  Open: [blockers or open decisions, or 'None']
🕐 STATE.md updated [timestamp]
```

---

## Critical Rego-Specific Traps
*(things that will break silently if you get them wrong)*

- **Z3 formula encoding** — if unsure how to encode an RBI rule as a Z3 formula, STOP and ask. A wrong formula gives a false COMPLIANT verdict. That is worse than a broken build.
- **Certificate immutability** — the `certificates` table in Supabase has no `updated_at` column. This is intentional. Never add one. A second write to the same `model_version` must return 409.
- **Three-layer imports** — ruff enforces `/features/ ↔ /pipeline/` cross-imports as build failures. If you get an import error from ruff, fix the architecture, not the linter rule.
- **LLM in hot path** — if you find yourself calling `llm_client` from inside `pipeline/ci/` or `pipeline/cd/`, stop. That violates AIRULES Rule 2.
- **CO interface Z3 output** — `reporter.py` translates Z3 counterexamples to plain English. The CO interface only ever receives the translation. If you are passing raw Z3 model output to a frontend component, it is going to the wrong place.
- **Neo4j single connection** — Aura free tier allows 1 concurrent connection. `max_size=1` in the connection pool. Do not increase this without upgrading the plan.
- **OpenRouter fallback** — if the default model (Claude 3.5 Sonnet) returns 429, fall back to `mistralai/mistral-7b-instruct` automatically. This is in `lib/llm_client.py`. Do not let a rate limit crash the ingestion pipeline.
