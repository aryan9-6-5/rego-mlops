import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';
import { StubApi, signIn } from './support';

const HASH = 'a1b2c3d4'.repeat(8);

const CERTIFICATE = {
  id: 'cert-1',
  model_version: 'v2.1.4',
  regulation_versions: [
    { version_id: 'RBI-4.1-20261007T120000000001Z', rule_id: 'RBI-4.1', formula_hash: 'f'.repeat(64) },
  ],
  proof_hash: HASH,
  hmac_signature: 'sig',
  created_at: '2026-10-07T12:30:00Z',
  verification: 'valid',
};

const COMPLIANT_RUN = {
  model_version: 'v2.1.4',
  status: 'compliant',
  gates: ['symbolic_check', 'reg_attack', 'fairness_check', 'regression'].map((gate) => ({
    gate,
    status: 'compliant',
    model_version: 'v2.1.4',
    rule_ids: [],
    duration_ms: 8,
    plain_english: 'ok',
    timestamp: '2026-10-07T12:00:00Z',
    violations: [],
  })),
};

test('a model is deployed by the engineer and the compliance officer downloads its certificate', async ({
  browser,
}) => {
  let deployed = false;
  const api = new StubApi();
  api
    .on((c) => (c.path === '/api/pipeline/status' ? { body: COMPLIANT_RUN } : undefined))
    .on((c) => {
      if (c.method === 'POST' && c.path === '/api/pipeline/deploy') {
        deployed = true;
        return { status: 201, body: { model_version: 'v2.1.4', certificate_id: 'cert-1', status: 'promoted' } };
      }
      return undefined;
    })
    .on((c) => (c.path === '/api/certificates/' ? { body: deployed ? [CERTIFICATE] : [] } : undefined));

  // --- ML engineer deploys -------------------------------------------------
  const engineer = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'] });
  const mle = await engineer.newPage();
  await api.install(mle);
  await signIn(mle, 'ml_engineer');
  await mle.goto('/pipeline');
  await mle.getByRole('button', { name: 'Deploy this model' }).click();
  expect(api.count('POST', '/api/pipeline/deploy')).toBe(0); // the first click only asks to confirm
  await expect(mle.getByText(/A certificate cannot be changed or removed/)).toBeVisible();
  await mle.getByRole('button', { name: 'Confirm deploy' }).click();
  await expect(mle.getByRole('status')).toContainText('Certificate cert-1 issued');
  await engineer.close();

  // --- Compliance officer downloads it -------------------------------------
  const officer = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'] });
  const co = await officer.newPage();
  await api.install(co);
  await signIn(co, 'compliance_officer');
  await co.goto('/certificates');

  await expect(co.getByText('v2.1.4')).toBeVisible();
  await expect(co.getByText('RBI section 4.1, version of 7 Oct 2026')).toBeVisible();
  const screenText = await co.locator('body').innerText();
  expect(screenText).not.toContain(HASH); // the hash is not shown to this role
  expect(screenText).not.toMatch(/Z3/);

  const [download] = await Promise.all([
    co.waitForEvent('download'),
    co.getByRole('button', { name: 'Download certificate' }).click(),
  ]);
  expect(download.suggestedFilename()).toBe('certificate-v2.1.4.json');
  const file = JSON.parse(await readFile((await download.path()) as string, 'utf-8'));
  expect(file.model_version).toBe('v2.1.4');
  expect(file.proof_hash).toBe(HASH); // the file carries it, for the auditor
  expect(file.regulation_versions[0].rule_id).toBe('RBI-4.1');
  expect(file).not.toHaveProperty('verification');

  // "Copy hash" puts it on the clipboard even though it is not on screen.
  await co.getByRole('button', { name: 'Copy hash' }).click();
  await expect(co.getByText('Hash copied')).toBeVisible();
  expect(await co.evaluate(() => navigator.clipboard.readText())).toBe(HASH);
  await officer.close();
});

test('a tampered certificate is shown as failed and cannot be downloaded', async ({ page }) => {
  const api = new StubApi();
  api.on((c) =>
    c.path === '/api/certificates/'
      ? {
          body: [
            { ...CERTIFICATE, verification: 'tampered', proof_hash: '', hmac_signature: '', regulation_versions: [] },
          ],
        }
      : undefined,
  );
  await api.install(page);
  await signIn(page, 'compliance_officer');
  await page.goto('/certificates');

  await expect(page.getByRole('alert')).toContainText('Verification failed');
  await expect(page.getByRole('button', { name: /Download certificate|Copy hash/ })).toHaveCount(0);
});

test('with no certificates the page explains why instead of showing nothing', async ({ page }) => {
  const api = new StubApi();
  api.on((c) => (c.path === '/api/certificates/' ? { body: [] } : undefined));
  await api.install(page);
  await signIn(page, 'compliance_officer');
  await page.goto('/certificates');
  await expect(page.getByText(/No certificates have been issued yet/)).toBeVisible();
});
