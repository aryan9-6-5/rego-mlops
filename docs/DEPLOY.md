# Deploying Rego to Railway

This guide deploys one container that serves both the API and the built web app. It lists what to prepare, the exact settings, how to check the result, and what is not yet verified. Nothing here has been run against a real Railway project. The production configuration was run locally and passes the checks in section 6.

## 1. What you need first

| Item | Notes |
|:---|:---|
| Supabase project | Run `supabase/migrations/01` to `08` in order. Note the project URL, the anon key and the service key |
| Neo4j instance | Neo4j Aura Free is enough. Note the connection URI (it starts with `neo4j+s://`), user and password |
| OpenRouter API key | Used only to draft rules from regulatory text |
| GitHub personal access token | Allowed to run workflows on this repository. Used by the manual training trigger |
| Railway account | Two services are needed, the main service and a canary service |
| A 32 byte or longer secret | For `PROOF_CERT_SECRET`. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

## 2. Create the services

1. In Railway, create a project from the GitHub repository. Railway reads `railway.json`, which selects the `Dockerfile` and the health check path `/health/`.
2. Name this service the main service. Note its service id.
3. Create a second service from the same repository for the canary. Note its service id. It receives no live traffic.
4. In Account Settings, create an API token for the deployer. Note the project id and environment id from the project settings.

## 3. Variables for the main service

Set these in the Railway dashboard. Do not commit any of them.

Build time (public values, baked into the browser bundle):

| Variable | Value |
|:---|:---|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key |

Never set a service key in a `VITE_` variable. The `Dockerfile` sets `VITE_API_BASE_URL=/api` itself, because the page and the API share one origin.

Runtime:

| Variable | Value |
|:---|:---|
| `ENVIRONMENT` | `production`. This turns off the API documentation pages |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Supabase URL and the service key. The service key stays on the server |
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | From Neo4j Aura |
| `OPENROUTER_API_KEY`, `LLM_DEFAULT_MODEL`, `LLM_FALLBACK_MODEL` | From `.env.example` |
| `PROOF_CERT_SECRET` | The 32 byte or longer secret. The server refuses to answer certificate requests without it |
| `GITHUB_TOKEN`, `GITHUB_REPOSITORY` | For the manual training trigger. Repository is `owner/name` |
| `RAILWAY_API_TOKEN`, `RAILWAY_PROJECT_ID`, `RAILWAY_ENVIRONMENT_ID`, `RAILWAY_SERVICE_ID`, `RAILWAY_CANARY_SERVICE_ID` | For the deployer |

Railway sets `PORT` itself. The container starts with `uvicorn` on that port.

## 4. Supabase settings

In Authentication, URL Configuration, set the site URL and the redirect URLs to the Railway address. Add the demo or real users and their rows in the `users` table (see `scripts/create_demo_users.py`).

## 5. GitHub settings

For `ct.yml`, add these repository secrets: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `KAGGLE_USERNAME`, `KAGGLE_KEY`, `KAGGLE_TRAIN_DATASET`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. Training needs a Kaggle dataset containing a training CSV, which this repository does not include. The CSV must not contain personal data columns; the notebook refuses to run if it does.

## 6. Check the deployment

Replace `HOST` with the Railway address.

```bash
curl -i https://HOST/health/              # 200, {"status":"ok",...}
curl -i https://HOST/health/z3            # 200, shows the Z3 version, 4.12.6
curl -i https://HOST/api/regulations/     # 401, no login
curl -i https://HOST/docs                 # returns the web app, not API documentation
```

Open the address in a browser. You should see the sign-in page. Sign in as each role and confirm that the compliance officer lands on the compliance dashboard and the ML engineer on the engineering dashboard.

The same configuration can be run locally without Docker to check it before deploying: build the frontend with `VITE_API_BASE_URL=/api`, then start `uvicorn src.api.main:app` with `ENVIRONMENT=production` and `FRONTEND_DIST=frontend/dist`.

## 7. Free tier behaviour

- The service sleeps when idle and takes roughly 30 seconds to wake. Before any timed demonstration, request `/health/` about five minutes ahead.
- The container filesystem is not persistent.
- Memory is limited. Z3 and the API fit comfortably in the limit stated in `docs/CONSTRAINTS.md`.

## 8. Open issue: how model files reach the API

The deploy and submit routes read a model folder (`profile.json` and `evaluation.json`) from `MODEL_ARTIFACT_DIR` on the API's own disk. On Railway that disk is not persistent, and a model produced by the training workflow in GitHub Actions is not on it. As built, a trained model cannot be deployed through the API in production.

Options, to be decided by the project owner:

1. Store bundles in Supabase Storage (free tier, 1 GB) and have the API read them from there. This needs a small change to the model file loader and a write step in `ct.yml`.
2. Upload the bundle through the API from the training workflow before submitting.
3. For a demonstration only, generate the demo bundles inside the running container with `scripts/make_demo_models.py`. They disappear when the container restarts.

## 9. Not verified

- The Railway GraphQL calls made by the deployer were written from Railway's public schema and have not been run against a real project.
- Railway cannot split traffic by percentage, so the canary takes no live traffic.
- Time to run one proof on the free tier has not been measured. Locally a single proof takes tens of milliseconds.
- Supabase row level security (migration 08) and Realtime have not been run against a real project. Try each role through the Supabase REST API after applying the migrations.

## 10. Checklist

- [ ] Migrations 01 to 08 applied
- [ ] Users and their `users` rows created
- [ ] Railway variables set, with `ENVIRONMENT=production`
- [ ] Main and canary services created
- [ ] First deploy healthy at `/health/`
- [ ] `/health/z3` reports Z3 4.12.6
- [ ] Each role signs in and sees the right interface
- [ ] GitHub secrets set for the training workflow
- [ ] The model file transport (section 8) decided
- [ ] Live address recorded in `README.md` and `docs/STATE.md`
