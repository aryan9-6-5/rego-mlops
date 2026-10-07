import { defineConfig } from '@playwright/test';

const PORT = Number(process.env.E2E_PORT ?? 5174);

/**
 * UI end-to-end tests. They run the real frontend against a stubbed API and a
 * stubbed Supabase (see tests/e2e/support.ts), so no backend, database or
 * network is needed. They use the Chrome already installed on the machine.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${PORT}`,
    channel: process.env.E2E_BROWSER_CHANNEL ?? 'chrome',
    permissions: ['clipboard-read', 'clipboard-write'],
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    env: {
      VITE_SUPABASE_URL: 'http://127.0.0.1:54321',
      VITE_SUPABASE_ANON_KEY: 'e2e-anon-key',
      VITE_API_BASE_URL: 'http://127.0.0.1:8000/api',
    },
  },
});
