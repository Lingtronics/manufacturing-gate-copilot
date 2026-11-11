import { defineConfig } from "@playwright/test";
import offline from "./playwright.config";
const server = offline.webServer;
if (!server || Array.isArray(server))
  throw new Error("Expected one local server");
export default defineConfig({
  ...offline,
  testDir: "./live-e2e",
  timeout: 90000,
  webServer: {
    ...server,
    env: {
      ...server.env,
      LLM_ENABLED: "true",
      LLM_MODEL: process.env.LLM_MODEL || "llama3.2:1b",
      LLM_TIMEOUT_SECONDS: "30",
    },
  },
});
