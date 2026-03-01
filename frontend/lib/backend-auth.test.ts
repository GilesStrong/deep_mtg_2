import { beforeEach, describe, expect, it, vi } from "vitest";

import { backendFetch, clearBackendTokens, ensureBackendTokens } from "@/lib/backend-auth";

const mockResponse = ({
    ok,
    status,
    json,
}: {
    ok: boolean;
    status: number;
    json?: unknown;
}): Response =>
({
    ok,
    status,
    json: vi.fn().mockResolvedValue(json ?? {}),
} as unknown as Response);

describe("backend-auth", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it("ensureBackendTokens exchanges backend tokens via secure cookie route", async () => {
        const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
            mockResponse({
                ok: true,
                status: 200,
                json: { ok: true },
            }),
        );

        await ensureBackendTokens({
            user: { email: "user@test.dev", googleAuthToken: "google-id-token" },
        } as never);

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(fetchMock).toHaveBeenCalledWith(
            "/backend-auth/exchange",
            expect.objectContaining({
                method: "POST",
                credentials: "same-origin",
            }),
        );
    });

    it("ensureBackendTokens throws when session is missing Google ID token", async () => {
        await expect(ensureBackendTokens({ user: { email: "user@test.dev" } } as never)).rejects.toThrow(
            "Missing Google ID token in session",
        );
    });

    it("backendFetch refreshes cookie-backed token after 401 and retries", async () => {
        let protectedRequestCount = 0;
        const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
            const url = String(input);
            if (url === "/backend-auth/exchange") {
                return mockResponse({ ok: true, status: 200, json: { ok: true } });
            }

            if (url === "/api/protected") {
                protectedRequestCount += 1;
                if (protectedRequestCount === 1) {
                    return mockResponse({ ok: false, status: 401 });
                }
                if (protectedRequestCount === 2) {
                    return mockResponse({ ok: true, status: 200 });
                }
            }

            if (url === "/backend-auth/refresh") {
                return mockResponse({ ok: true, status: 200, json: { ok: true } });
            }

            return mockResponse({ ok: false, status: 500 });
        });

        const response = await backendFetch(
            { user: { email: "user@test.dev", googleAuthToken: "google-id-token" } } as never,
            "/api/protected",
        );

        expect(response.status).toBe(200);
        expect(protectedRequestCount).toBe(2);
        expect(fetchMock).toHaveBeenCalledWith(
            "/backend-auth/refresh",
            expect.objectContaining({ method: "POST", credentials: "same-origin" }),
        );
    });

    it("clearBackendTokens clears cookie-backed tokens via API route", () => {
        const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
            mockResponse({ ok: true, status: 200, json: { ok: true } }),
        );

        clearBackendTokens();

        expect(fetchMock).toHaveBeenCalledWith(
            "/backend-auth/clear",
            expect.objectContaining({
                method: "POST",
                credentials: "same-origin",
            }),
        );
    });
});
