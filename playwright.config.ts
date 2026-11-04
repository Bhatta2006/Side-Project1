import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const scripts = path.resolve('.venv', process.platform === 'win32' ? 'Scripts' : 'bin');
const executable = (name: string) => `"${path.join(scripts, `${name}${process.platform === 'win32' ? '.exe' : ''}`)}"`;
// Set PW_CHANNEL=msedge (or chrome) to use an installed browser instead of Playwright's Chromium.
const channel = process.env.PW_CHANNEL || undefined;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  // The dev server compiles each route on first visit; give cold navigations room.
  expect: { timeout: 15_000 },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    // Fresh learners get the first-run tour; tests skip it unless they clear this (see tour.spec.ts).
    storageState: { cookies: [], origins: [{ origin: 'http://localhost:3000', localStorage: [{ name: 'socrat:tour-seen', value: '1' }] }] },
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], channel } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium', channel } },
  ],
  webServer: [
    {
      // A fresh database every run: a leftover file from another branch can sit at a schema
      // revision this branch does not know, and then the server cannot start.
      command: `${executable('python')} -c "import pathlib; [pathlib.Path('socrat.e2e.db' + s).unlink(missing_ok=True) for s in ('', '-wal', '-shm')]" && ${executable('alembic')} upgrade head && ${executable('python')} scripts/content/build.py && ${executable('uvicorn')} socrat.main:create_app --factory --app-dir services/api/src --host 127.0.0.1 --port 8000 --loop socrat.dev_loop:loop_factory`,
      url: 'http://127.0.0.1:8000/api/health/ready',
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: {
        SOCRAT_ENVIRONMENT: 'test',
        SOCRAT_DATABASE_URL: 'sqlite:///socrat.e2e.db',
        SOCRAT_DEV_LOGIN_ENABLED: 'true',
        SOCRAT_AI_PROVIDER: 'offline',
        SOCRAT_PREWARM_CONTENT: 'true',
        SOCRAT_LITE_MODE_ENABLED: 'true',
        SOCRAT_PUBLIC_ORIGIN: 'http://localhost:3000',
      },
    },
    { command: 'npm run dev', url: 'http://localhost:3000', reuseExistingServer: !process.env.CI, timeout: 120_000 },
  ],
});
