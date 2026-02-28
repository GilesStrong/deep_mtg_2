import { beforeEach, describe, expect, it, vi } from "vitest";

import { backendFetch, clearBackendTokens, ensureBackendTokens } from "@/lib/backend-auth";

const ACCESS_TOKEN_KEY = "deep_mtg_backend_access_token";
const REFRESH_TOKEN_KEY = "deep_mtg_backend_refresh_token";
const USER_EMAIL_KEY = "deep_mtg_backend_user_email";

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
        window.localStorage.clear();
    });

    it("ensureBackendTokens exchanges and stores tokens when cache is empty", async () => {
        const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
            mockResponse({
                ok: true,
                status: 200,
                json: { access_token: "access-1", refresh_token: "refresh-1" },
            }),
        );

        const tokens = await ensureBackendTokens({
            user: { email: "user@test.dev", googleAuthToken: "google-id-token" },
        } as never);

        expect(tokens).toEqual({ accessToken: "access-1", refreshToken: "refresh-1" });
        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(window.localStorage.getItem(ACCESS_TOKEN_KEY)).toBe("access-1");
        expect(window.localStorage.getItem(REFRESH_TOKEN_KEY)).toBe("refresh-1");
        expect(window.localStorage.getItem(USER_EMAIL_KEY)).toBe("user@test.dev");
    });

    it("ensureBackendTokens returns stored tokens without network call", async () => {
        window.localStorage.setItem(ACCESS_TOKEN_KEY, "cached-access");
        window.localStorage.setItem(REFRESH_TOKEN_KEY, "cached-refresh");
        window.localStorage.setItem(USER_EMAIL_KEY, "user@test.dev");

        const fetchMock = vi.spyOn(globalThis, "fetch");

        const tokens = await ensureBackendTokens({
            user: { email: "user@test.dev", googleAuthToken: "google-id-token" },
        } as never);

        expect(tokens).toEqual({ accessToken: "cached-access", refreshToken: "cached-refresh" });
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("backendFetch refreshes access token after 401 and retries", async () => {
        window.localStorage.setItem(ACCESS_TOKEN_KEY, "stale-access");
        window.localStorage.setItem(REFRESH_TOKEN_KEY, "stale-refresh");
        window.localStorage.setItem(USER_EMAIL_KEY, "user@test.dev");

        const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
            const url = String(input);
            if (url === "/api/protected") {
                const authHeader = (init?.headers as Headers).get("Authorization");
                if (authHeader === "Bearer stale-access") {
                    return mockResponse({ ok: false, status: 401 });
                }
                if (authHeader === "Bearer refreshed-access") {
                    return mockResponse({ ok: true, status: 200 });
                }
            }

            if (url === "/api/app/token/refresh") {
                return mockResponse({
                    ok: true,
                    status: 200,
                    json: { access_token: "refreshed-access", refresh_token: "refreshed-refresh" },
                });
            }

            return mockResponse({ ok: false, status: 500 });
        });

        const response = await backendFetch(
            { user: { email: "user@test.dev", googleAuthToken: "google-id-token" } } as never,
            "/api/protected",
        );

        expect(response.status).toBe(200);
        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(window.localStorage.getItem(ACCESS_TOKEN_KEY)).toBe("refreshed-access");
        expect(window.localStorage.getItem(REFRESH_TOKEN_KEY)).toBe("refreshed-refresh");
    });

    it("clearBackendTokens removes all cached values", () => {
        window.localStorage.setItem(ACCESS_TOKEN_KEY, "access");
        window.localStorage.setItem(REFRESH_TOKEN_KEY, "refresh");
        window.localStorage.setItem(USER_EMAIL_KEY, "user@test.dev");

        clearBackendTokens();

        expect(window.localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
        expect(window.localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
        expect(window.localStorage.getItem(USER_EMAIL_KEY)).toBeNull();
    });
});
