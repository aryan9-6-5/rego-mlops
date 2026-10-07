import { expect, test } from '@playwright/test';
import { StubApi, signIn } from './support';

const EXPLANATION =
  'This model breaks rule RBI-4.1 (section 4.1). Models must not use PIN codes. Features involved: pin code.';

const VIOLATION_RUN = {
  model_version: 'bad-model',
  status: 'violation',
  gates: [
    {
      gate: 'symbolic_check',
      status: 'violation',
      model_version: 'bad-model',
      rule_ids: ['RBI-4.1'],
      duration_ms: 12,
      plain_english: 'The model breaks 1 of 1 active rules.',
      timestamp: '2026-10-07T12:00:00Z',
      violations: [
        {
          rule_id: 'RBI-4.1',
          plain_english: EXPLANATION,
          counterexample: { pin_code_weight: '3/10' },
        },
      ],
    },
    ...['reg_attack', 'fairness_check', 'regression'].map((gate) => ({
      gate,
      status: 'skipped',
      model_version: 'bad-model',
      rule_ids: [],
      duration_ms: 0,
      plain_english: 'Not run because symbolic_check failed.',
      timestamp: '2026-10-07T12:00:00Z',
      violations: [],
    })),
  ],
};

test('the ML engineer sees the exact violation, with the Z3 counterexample', async ({ page }) => {
  const api = new StubApi();
  let submitted = false;
  api
    .on((c) => {
      if (c.method === 'POST' && c.path === '/api/pipeline/submit') {
        submitted = true;
        return { status: 202, body: { model_version: 'bad-model', status: 'accepted' } };
      }
      return undefined;
    })
    .on((c) => (c.path === '/api/pipeline/status' ? { body: submitted ? VIOLATION_RUN : null } : undefined));
  await api.install(page);
  await signIn(page, 'ml_engineer');

  await page.goto('/pipeline');
  await expect(page.getByText(/No model has been submitted yet/)).toBeVisible();

  await page.getByLabel('Model bundle folder').fill('bad-model');
  await page.getByRole('button', { name: 'Run compliance gates' }).click();

  // Gate rows: the first failed, the rest were never run.
  const rows = page.locator('tbody tr');
  await expect(rows).toHaveCount(4);
  await expect(rows.nth(0)).toContainText('Symbolic check (Z3)');
  await expect(rows.nth(0)).toContainText('Violation');
  for (const index of [1, 2, 3]) await expect(rows.nth(index)).toContainText('Skipped');
  expect(api.calls.find((c) => c.path === '/api/pipeline/submit')?.body).toEqual({
    artifact_path: 'bad-model',
  });

  // The report names the rule, explains it, and shows the counterexample.
  await page.getByRole('link', { name: 'View the violation report' }).click();
  await expect(page.getByText('RBI-4.1', { exact: true })).toBeVisible();
  await expect(page.getByText(EXPLANATION)).toBeVisible();
  await expect(page.getByText('Z3 counterexample')).toBeVisible();
  await expect(page.getByRole('cell', { name: 'pin_code_weight' })).toBeVisible();
  await expect(page.getByRole('cell', { name: '3/10' })).toBeVisible();
});

test('the compliance officer sees the violation in plain English only, and cannot open the report', async ({
  page,
}) => {
  const api = new StubApi();
  api
    .on((c) =>
      c.path === '/api/regulations/'
        ? {
            body: [
              {
                id: 'reg-1',
                rule_id: 'RBI-4.1',
                jurisdiction: 'India',
                source_text: 'x',
                description: 'Models must not use PIN codes.',
                formal_logic: '(assert (= pin_code_weight 0))',
                status: 'active',
                version: '20261007T100000000001Z',
                validation_message: null,
              },
            ],
          }
        : undefined,
    )
    .on((c) =>
      c.path === '/api/certificates/'
        ? {
            body: [
              {
                id: 'cert-1',
                model_version: 'v1',
                regulation_versions: [
                  { version_id: 'RBI-4.1-20261007T100000000001Z', rule_id: 'RBI-4.1', formula_hash: 'ab' },
                ],
                proof_hash: 'c'.repeat(64),
                hmac_signature: 'sig',
                created_at: '2026-10-07T10:30:00Z',
                verification: 'valid',
              },
            ],
          }
        : undefined,
    );
  await api.install(page);
  // A gate failed after the last certificate was issued.
  await signIn(page, 'compliance_officer', [
    {
      id: 'evt-1',
      stage: 'ci',
      gate_name: 'symbolic_check',
      status: 'violation',
      model_version: 'bad-model',
      rule_ids: ['RBI-4.1'],
      duration_ms: 12,
      plain_english_result: 'The model breaks 1 of 1 active rules.',
      created_at: '2026-10-07T11:00:00Z',
    },
  ]);

  await page.goto('/');
  const hero = page.getByRole('status').first();
  await expect(hero).toContainText('Violation');
  await expect(hero).toContainText('A new model did not pass a compliance check');

  const text = (await page.locator('body').innerText()).toLowerCase();
  for (const technical of ['pin_code_weight', '3/10', 'rbi-4.1', 'z3', 'counterexample', 'c'.repeat(20)]) {
    expect(text, `the compliance officer screen must not contain "${technical}"`).not.toContain(technical);
  }

  // The engineer-only pages are closed to this role.
  await page.goto('/violation-report');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await page.goto('/pipeline');
  await expect(page).toHaveURL(/\/unauthorized$/);
  expect(api.count('GET', '/api/pipeline/status')).toBe(0);
});
