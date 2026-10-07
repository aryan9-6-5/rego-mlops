import { expect, test } from '@playwright/test';
import { StubApi, signIn } from './support';

const SOURCE = 'Regulated Entities shall not use geographic proxies such as PIN codes.';

function pendingRule(status: 'pending_approval' | 'active') {
  return {
    id: 'reg-1',
    rule_id: 'RBI-4.1',
    jurisdiction: 'India',
    source_text: SOURCE,
    description: 'Lending models must not use PIN codes.',
    formal_logic: '(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))',
    status,
    version: '20261007T120000000001Z',
    validation_message: null,
  };
}

test('compliance officer pastes a regulation, reviews the rule and approves it in two steps', async ({
  page,
}) => {
  const api = new StubApi();
  let extracted = false;
  let approved = false;
  api
    .on((c) => (c.method === 'POST' && c.path === '/api/regulations/' ? { status: 202, body: { job_id: 'job-1' } } : undefined))
    .on((c) => {
      if (c.path !== '/api/regulations/jobs/job-1') return undefined;
      extracted = true;
      return { body: { job_id: 'job-1', status: 'complete', error: null } };
    })
    .on((c) => {
      if (c.method === 'GET' && c.path === '/api/regulations/') {
        const rules = extracted ? [pendingRule(approved ? 'active' : 'pending_approval')] : [];
        return { body: rules };
      }
      return undefined;
    })
    .on((c) => {
      if (c.method === 'POST' && c.path === '/api/regulations/reg-1/approve') {
        approved = true;
        return { body: pendingRule('active') };
      }
      return undefined;
    });
  await api.install(page);
  await signIn(page, 'compliance_officer');

  // Paste the regulation. Empty submit first: errors appear inline and nothing is sent.
  await page.goto('/regulations');
  await page.getByRole('button', { name: 'Extract rules' }).click();
  await expect(page.getByText('Enter the section, for example 4.1.')).toBeVisible();
  await expect(page.getByText('Paste the regulatory text or drop a text file.')).toBeVisible();
  expect(api.count('POST', '/api/regulations/')).toBe(0);

  await page.getByPlaceholder('4.1').fill('4.1');
  await page.getByLabel('Regulatory text').fill(SOURCE);
  await page.getByRole('button', { name: 'Extract rules' }).click();

  await expect(page.getByText('Rules extracted')).toBeVisible();
  expect(api.calls.find((c) => c.method === 'POST' && c.path === '/api/regulations/')?.body).toEqual({
    section: '4.1',
    content: SOURCE,
  });

  // Review: one rule, source text beside a plain-English meaning, no jargon.
  await page.getByRole('link', { name: 'Go to approval queue' }).click();
  await page.getByText('Lending models must not use PIN codes.').click();
  await expect(page.getByText('Review this rule')).toBeVisible();
  await expect(page.getByText(SOURCE)).toBeVisible();
  await expect(page.getByText('The weight of pin code equals 0.')).toBeVisible();
  const body = (await page.locator('body').innerText()).toLowerCase();
  expect(body).not.toContain('declare-const');
  expect(body).not.toContain('rbi-4.1');
  expect(body).not.toContain('z3');

  // Approve takes two deliberate actions. The first click calls nothing.
  await page.getByRole('button', { name: 'Yes, approve rule' }).click();
  expect(api.count('POST', '/approve')).toBe(0);
  const activate = page.getByRole('button', { name: 'Activate rule' });
  await expect(activate).toBeDisabled();
  await page.getByRole('textbox').fill('activate');
  await expect(activate).toBeDisabled();
  await page.getByRole('textbox').fill('ACTIVATE');
  await expect(activate).toBeEnabled();
  await activate.click();

  await expect.poll(() => api.count('POST', '/approve')).toBe(1);
  await expect(page.getByText('Active rules')).toBeVisible();
  await expect(page.getByText('No rules are waiting for review.')).toBeVisible();
});

test('an LLM failure shows inline in the compliance officer interface and does not crash it', async ({
  page,
}) => {
  const api = new StubApi();
  api
    .on((c) => (c.method === 'POST' && c.path === '/api/regulations/' ? { status: 202, body: { job_id: 'job-2' } } : undefined))
    .on((c) =>
      c.path === '/api/regulations/jobs/job-2'
        ? { body: { job_id: 'job-2', status: 'failed', error: 'Rule extraction failed. Please try again or check the regulatory text.' } }
        : undefined,
    )
    .on((c) => (c.method === 'GET' && c.path === '/api/regulations/' ? { body: [] } : undefined));
  await api.install(page);
  await signIn(page, 'compliance_officer');

  await page.goto('/regulations');
  await page.getByPlaceholder('4.1').fill('4.1');
  await page.getByLabel('Regulatory text').fill(SOURCE);
  await page.getByRole('button', { name: 'Extract rules' }).click();

  await expect(page.getByRole('alert')).toContainText('Rule extraction failed. Please try again');
  await expect(page.getByRole('button', { name: 'Extract rules' })).toBeVisible();
});
