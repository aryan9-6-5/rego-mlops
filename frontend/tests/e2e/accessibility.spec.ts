import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { StubApi, signIn, type Role } from './support';

/**
 * Accessibility audit with axe-core (the engine behind Lighthouse's accessibility
 * score), against the real pages with stubbed data. WCAG 2.0/2.1 A and AA rules.
 * This checks what a tool can check: labels, names, roles, contrast, ARIA. It does
 * not replace a screen reader pass.
 */

const RULE = {
  id: 'reg-1',
  rule_id: 'RBI-4.1',
  jurisdiction: 'India',
  source_text: 'Lending models shall not use PIN codes.',
  description: 'Lending models must not use PIN codes.',
  formal_logic: '(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))',
  status: 'pending_approval',
  version: '20261007T120000000001Z',
  validation_message: null,
};
const ACTIVE = { ...RULE, id: 'reg-2', status: 'active', version: '20261007T100000000001Z' };
const FAILED = {
  ...RULE,
  id: 'reg-3',
  status: 'z3_rejected',
  validation_message: 'The rule is always true, so it would not restrict anything.',
};
const CERT = {
  id: 'cert-1',
  model_version: 'v2.1.4',
  regulation_versions: [
    { version_id: 'RBI-4.1-20261007T100000000001Z', rule_id: 'RBI-4.1', formula_hash: 'ab' },
  ],
  proof_hash: 'c'.repeat(64),
  hmac_signature: 'sig',
  created_at: '2026-10-07T10:30:00Z',
  verification: 'valid',
};
const TAMPERED = { ...CERT, id: 'cert-2', verification: 'tampered', proof_hash: '', regulation_versions: [] };
const GATE = (gate: string, status: string, violations: unknown[] = []) => ({
  gate,
  status,
  model_version: 'bad',
  rule_ids: ['RBI-4.1'],
  duration_ms: 9,
  plain_english: 'The model breaks 1 of 1 active rules.',
  timestamp: '2026-10-07T12:00:00Z',
  violations,
});
const RUN = {
  model_version: 'bad',
  status: 'violation',
  gates: [
    GATE('symbolic_check', 'violation', [
      { rule_id: 'RBI-4.1', plain_english: 'This model breaks rule RBI-4.1.', counterexample: { pin_code_weight: '3/10' } },
    ]),
    GATE('reg_attack', 'skipped'),
    GATE('fairness_check', 'skipped'),
    GATE('regression', 'skipped'),
  ],
};
const EVENT = {
  id: 'e1',
  stage: 'ci',
  gate_name: 'symbolic_check',
  status: 'violation',
  model_version: 'bad',
  rule_ids: [],
  duration_ms: 9,
  plain_english_result: 'x',
  created_at: '2026-10-07T12:00:00Z',
};

async function stub(page: Page, role: Role): Promise<StubApi> {
  const api = new StubApi();
  api
    .on((c) => (c.path === '/api/regulations/' ? { body: [RULE, ACTIVE, FAILED] } : undefined))
    .on((c) => (c.path === '/api/certificates/' ? { body: [CERT, TAMPERED] } : undefined))
    .on((c) => (c.path === '/api/pipeline/status' ? { body: RUN } : undefined))
    .on((c) => (c.path === '/api/pipeline/drift-log' ? { body: [] } : undefined))
    .on((c) =>
      c.path === '/api/models/'
        ? { body: [{ model_version: 'v2.1.4', created_at: '2026-10-07T10:30:00Z', regulation_versions: [] }] }
        : undefined,
    );
  await api.install(page);
  await signIn(page, role, [EVENT]);
  return api;
}

async function audit(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  return results.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ") + " <" + n.html.slice(0, 90) + ">").join(' | ')}`);
}

const CO_PAGES = ['/', '/regulations', '/approval-queue', '/certificates'];
const MLE_PAGES = ['/', '/pipeline', '/violation-report', '/model-registry', '/model-diff'];

for (const path of CO_PAGES) {
  test(`compliance officer ${path} has no WCAG A/AA violations`, async ({ page }) => {
    await stub(page, 'compliance_officer');
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    expect(await audit(page)).toEqual([]);
  });
}

for (const path of MLE_PAGES) {
  test(`ML engineer ${path} has no WCAG A/AA violations`, async ({ page }) => {
    await stub(page, 'ml_engineer');
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    expect(await audit(page)).toEqual([]);
  });
}

test('the login page has no violations', async ({ page }) => {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  expect(await audit(page)).toEqual([]);
});

test('the rule review card and its confirmation steps have no violations', async ({ page }) => {
  await stub(page, 'compliance_officer');
  await page.goto('/approval-queue');
  await page.getByText('Lending models must not use PIN codes.').first().click();
  expect(await audit(page)).toEqual([]);
  await page.getByRole('button', { name: 'Yes, approve rule' }).click();
  expect(await audit(page)).toEqual([]);
  await page.getByRole('button', { name: 'Go back' }).click();
  await page.getByRole('button', { name: 'No, reject rule' }).click();
  expect(await audit(page)).toEqual([]);
});

test('the upload form shows inline errors that pass the audit', async ({ page }) => {
  await stub(page, 'compliance_officer');
  await page.goto('/regulations');
  await page.getByRole('button', { name: 'Extract rules' }).click();
  await expect(page.getByRole('alert').first()).toBeVisible();
  expect(await audit(page)).toEqual([]);
});

test('every form field has a label', async ({ page }) => {
  await stub(page, 'compliance_officer');
  await page.goto('/regulations');
  const unlabelled = await page.locator('input:not([type=hidden]), textarea, select').evaluateAll((fields) =>
    fields
      .filter((f) => {
        const el = f as HTMLInputElement;
        return !(el.labels && el.labels.length) && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby');
      })
      .map((f) => f.outerHTML.slice(0, 80)),
  );
  expect(unlabelled).toEqual([]);
});

test('the approve and reject flow works from the keyboard alone', async ({ page }) => {
  const api = await stub(page, 'compliance_officer');
  api.on((c) => (c.method === 'POST' && c.path.endsWith('/approve') ? { body: { ...RULE, status: 'active' } } : undefined));
  await page.goto('/approval-queue');

  // Open the rule with Enter on its row.
  await page.getByRole('button', { name: /Lending models must not use PIN codes/ }).first().focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Review this rule')).toBeVisible();

  // Approve: focus, Enter, type the word, move on, Enter.
  await page.getByRole('button', { name: 'Yes, approve rule' }).focus();
  await page.keyboard.press('Enter');
  expect(api.count('POST', '/approve')).toBe(0);
  await page.getByRole('textbox').focus();
  await page.keyboard.type('ACTIVATE');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Activate rule' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect.poll(() => api.count('POST', '/approve')).toBe(1);
});

test('keyboard users can reach every control on the review card in order', async ({ page }) => {
  await stub(page, 'compliance_officer');
  await page.goto('/approval-queue');
  await page.getByText('Lending models must not use PIN codes.').first().click();
  await page.getByRole('button', { name: 'Yes, approve rule' }).focus();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'No, reject rule' })).toBeFocused();
});

test('prefers-reduced-motion switches the animations and transitions off', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await stub(page, 'compliance_officer');
  await page.goto('/');
  const hero = page.getByRole('status').first();
  await expect(hero).toContainText('Violation');
  const timings = await page.evaluate(() => {
    const seconds = (value: string) => Math.max(...value.split(',').map((v) => parseFloat(v)));
    const hero = document.querySelector('[role=status]') as HTMLElement;
    const dot = document.querySelector('.animate-pulse') as HTMLElement;
    return {
      transition: seconds(getComputedStyle(hero).transitionDuration),
      animation: seconds(getComputedStyle(dot).animationDuration),
    };
  });
  expect(timings.transition).toBeLessThan(0.001);
  expect(timings.animation).toBeLessThan(0.001);
});

test('without that preference the violation dot still pulses', async ({ page }) => {
  await stub(page, 'compliance_officer');
  await page.goto('/');
  await expect(page.getByRole('status').first()).toContainText('Violation');
  const animation = await page.evaluate(() =>
    parseFloat(getComputedStyle(document.querySelector('.animate-pulse') as HTMLElement).animationDuration),
  );
  expect(animation).toBeGreaterThan(0.5);
});
