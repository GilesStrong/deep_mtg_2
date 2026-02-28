import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3001";
const isCI = Boolean(process.env.CI);

export default defineConfig({
    testDir: "./e2e/tests",
    fullyParallel: false,
    forbidOnly: isCI,
    retries: isCI ? 2 : 0,
    workers: isCI ? 1 : undefined,
    reporter: [["list"], ["html", { open: "never" }]],
    use: {
        baseURL,
        trace: isCI ? "retain-on-failure" : "on-first-retry",
        video: isCI ? "retain-on-failure" : "off",
        screenshot: "only-on-failure",
    },
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
    ],
    webServer: {
        command: "bun run dev",
        url: baseURL,
        reuseExistingServer: !isCI,
        env: {
            ...process.env,
            NEXTAUTH_URL: baseURL,
            NEXTAUTH_SECRET:
                process.env.NEXTAUTH_SECRET ??
                "e2e-nextauth-secret-please-change-in-real-env-32chars",
            GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID ?? "e2e-google-client-id",
            GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET ?? "e2e-google-client-secret",
        },
    },
});
