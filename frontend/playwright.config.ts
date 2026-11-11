import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:8000",
    viewport: { width: 1440, height: 1100 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command:
      process.platform === "win32"
        ? "..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8000"
        : "../.venv/bin/python -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8000",
    url: "http://127.0.0.1:8000/health",
    reuseExistingServer: false,
    env: {
      DATABASE_PATH: `../data/e2e-${Date.now()}.sqlite3`,
      APP_MODE: "demo",
      MIRO_MODE: "mock",
      ALLOW_LIVE_MIRO: "false",
      LLM_ENABLED: "false",
    },
    timeout: 30000,
  },
});
