import type { Page, Request, Route } from '@playwright/test';

export const API = 'http://127.0.0.1:8000';
const SUPABASE = 'http://127.0.0.1:54321';

export type Role = 'compliance_officer' | 'ml_engineer';

const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,OPTIONS',
};

export interface ApiCall {
  method: string;
  path: string;
  body: unknown;
}

type Handler = (call: ApiCall) => { status?: number; body: unknown } | undefined;

/** Stubs the Rego API. Every request is recorded so a test can assert what was
 * (and was not) sent, for example that approve was not called by the first click. */
export class StubApi {
  calls: ApiCall[] = [];
  private handlers: Handler[] = [];

  on(handler: Handler): this {
    this.handlers.push(handler);
    return this;
  }

  count(method: string, pathPart: string): number {
    return this.calls.filter((c) => c.method === method && c.path.includes(pathPart)).length;
  }

  async install(page: Page): Promise<void> {
    await page.route(`${API}/**`, async (route: Route, request: Request) => {
      if (request.method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: CORS });
        return;
      }
      const url = new URL(request.url());
      const raw = request.postData();
      const call: ApiCall = {
        method: request.method(),
        path: url.pathname,
        body: raw ? JSON.parse(raw) : null,
      };
      this.calls.push(call);
      for (const handler of this.handlers) {
        const reply = handler(call);
        if (reply) {
          await route.fulfill({
            status: reply.status ?? 200,
            headers: { ...CORS, 'content-type': 'application/json' },
            body: JSON.stringify(reply.body),
          });
          return;
        }
      }
      await route.fulfill({ status: 404, headers: CORS, body: '{"detail":"not stubbed"}' });
    });
  }
}

/** Signs the browser in as `role` without a real Supabase: a stored session, a
 * stubbed users table, and (optionally) the CI events the dashboards read. */
export async function signIn(
  page: Page,
  role: Role,
  pipelineEvents: unknown[] = [],
): Promise<void> {
  const session = {
    access_token: 'e2e-access-token',
    refresh_token: 'e2e-refresh-token',
    token_type: 'bearer',
    expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    user: {
      id: `user-${role}`,
      aud: 'authenticated',
      email: `${role}@test.rego.dev`,
      app_metadata: {},
      user_metadata: {},
      created_at: '2026-01-01T00:00:00Z',
    },
  };
  await page.addInitScript((value) => {
    window.localStorage.setItem('sb-127-auth-token', JSON.stringify(value));
  }, session);

  await page.route(`${SUPABASE}/rest/v1/users*`, (route) =>
    route.fulfill({
      status: 200,
      headers: { ...CORS, 'content-type': 'application/json' },
      body: JSON.stringify({ role }),
    }),
  );
  await page.route(`${SUPABASE}/rest/v1/pipeline_events*`, (route) =>
    route.fulfill({
      status: 200,
      headers: { ...CORS, 'content-type': 'application/json' },
      body: JSON.stringify(pipelineEvents),
    }),
  );
  await page.route(`${SUPABASE}/auth/v1/**`, (route) =>
    route.fulfill({ status: 200, headers: { ...CORS, 'content-type': 'application/json' }, body: '{}' }),
  );
  // Realtime and the API socket are not under test here: let them fail quietly.
  await page.routeWebSocket(/realtime\/v1\/websocket|pipeline\/events/, (ws) => ws.close());
}
