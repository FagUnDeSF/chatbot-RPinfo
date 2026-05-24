import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/auth-real",
  timeout: 30_000,
  expect: {
    timeout: 5_000
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
