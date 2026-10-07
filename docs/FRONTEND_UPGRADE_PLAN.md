# Frontend dependency upgrade plan

Status: steps 1 and 2 are applied (October 2026). Step 3 (tailwindcss 4) is deferred.
Versions are pinned in docs/TECH.md, so each step below also needs a TECH.md edit.

## Why

`npm audit` in `frontend/` reports 7 vulnerabilities (2 moderate, 5 high, 1 of them
critical through a dev tool). `npm audit fix` changes nothing, because every fix is
a major version change.

| Package | Severity | Where it runs | Fixed by |
|---|---|---|---|
| react-router (via react-router-dom 6) | moderate | shipped to users | react-router-dom 7 |
| tinypool, vite-node, vitest, esbuild, vite | critical to moderate | development and test only | vite 8 and vitest 5 |
| braces, micromatch, fast-glob, chokidar, tailwindcss | high | build time only | tailwindcss 4 |
| postcss-selector-parser, postcss-nested | moderate | build time only | tailwindcss 4 |

Only the react-router advisory affects code that users load. `npm audit --omit=dev`
is clean once react-router-dom 7 is installed. The rest are tools that run on a
developer machine or in CI, so the practical risk is low, but the audit stays noisy
until they are upgraded.

## Trial results

Each trial was run on a copy of `frontend/` outside the repository and ran the same
checks: ESLint, 113 Vitest tests, `npm run build`, 24 Playwright end-to-end tests,
and `npm audit`.

| Trial | Change | Result |
|---|---|---|
| T0 | `npm audit fix` | No change. |
| T1 | react-router-dom ^7 (7.18.4) | Lint, 113 unit tests, build and 24 end-to-end tests all pass with no source changes. `npm audit --omit=dev` reports 0 vulnerabilities. |
| T2 | vite 8.3, vitest 5.0, @vitejs/plugin-react 6.1, jsdom 29, plus T1 | Fails to install with the project's @types/node 20. With @types/node ^22: lint, 113 unit tests and 24 end-to-end tests pass. The build fails until `lib` in `tsconfig.json` is raised from ES2020 to ES2022 (a test file uses `Array.prototype.at`); with that change the build passes. Full `npm audit` still reports 7 vulnerabilities because tailwindcss is unchanged; `--omit=dev` reports 0. |
| T3 | tailwindcss 4 | Not run. It is a migration, not a version bump (see step 3). |

## Steps, in the order to do them

### Step 1: react-router-dom 7 (recommended now)

- Change `react-router-dom` to `^7.18.0` in `frontend/package.json` and TECH.md.
- No source changes were needed in the trial.
- Clears the only advisory that reaches production.
- Run the usual checks. Risk: low.

### Step 2: Vite 8, Vitest 5, plugin-react 6, jsdom 29

Requirements found in the trial:

- `@types/node` must be ^22 or newer (Vitest 5 requires it).
- Vite 8 needs Node 20.19 or newer, or 22.12 or newer. The CI jobs use Node 20
  (`.github/workflows/ci.yml`, three places) and the Dockerfile uses `node:20-slim`.
  Move all four to Node 22, or confirm that the Node 20 builds resolve to 20.19 or
  newer, before merging.
- Raise `lib` in `frontend/tsconfig.json` to ES2022.
- Update `docs/TECH.md` for vite, vitest, @vitejs/plugin-react, jsdom, @types/node
  and the Node version.

Risk: medium. Everything passed in the trial, but the Node version change touches
CI and the Docker image, so run the CI workflow and the docker-image job once on a
branch before merging.

### Step 3: tailwindcss 4 (defer)

Tailwind 4 changes how it is configured: the JavaScript `tailwind.config.js` is
replaced by CSS directives, the PostCSS plugin moves to a separate package
(`@tailwindcss/postcss`), and some utility class names and defaults change. The
project's design tokens (docs/DESIGN.md) live in `tailwind.config.js`, so this step
needs a deliberate migration and a visual check of every page. The advisories it
fixes are build-time only.

Recommendation: do not do this as part of a security cleanup. Schedule it as its own
task, with a screenshot comparison of the role dashboards before and after. Until
then, accept the build-time advisories and say so in docs/ISSUES.md.

## Suggested order and checks

1. Branch. Apply step 1. Run `npm run lint`, `npm test`, `npm run build`,
   `npx playwright test`, `npm audit --omit=dev`. Merge.
2. Branch. Apply step 2 including the Node version change. Run the same checks
   locally, then the full GitHub Actions workflow. Merge.
3. Step 3 only when there is time for a visual review.

After steps 1 and 2, `npm audit --omit=dev` reports 0 and the remaining full-audit
findings are all tailwindcss build-time dependencies.
