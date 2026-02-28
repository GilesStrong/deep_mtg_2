import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockGetToken, mockRedirect, mockNext } = vi.hoisted(() => ({
    mockGetToken: vi.fn(),
    mockRedirect: vi.fn((url: URL) => ({ type: "redirect", url: url.toString() })),
    mockNext: vi.fn(() => ({ type: "next" })),
}));

vi.mock("next-auth/jwt", () => ({
    getToken: mockGetToken,
}));

vi.mock("next/server", () => ({
    NextResponse: {
        redirect: mockRedirect,
        next: mockNext,
    },
}));

import { config, proxy } from "@/proxy";

describe("proxy", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        process.env.NEXTAUTH_SECRET = "test-secret";
    });

    it("redirects unauthenticated users from protected routes", async () => {
        mockGetToken.mockResolvedValue(null);

        const response = await proxy({
            nextUrl: { pathname: "/dashboard" },
            url: "https://app.test/dashboard",
        } as never);

        expect(mockRedirect).toHaveBeenCalledTimes(1);
        expect(response).toEqual({ type: "redirect", url: "https://app.test/login" });
    });

    it("redirects authenticated users away from login", async () => {
        mockGetToken.mockResolvedValue({ sub: "user-id" });

        const response = await proxy({
            nextUrl: { pathname: "/login" },
            url: "https://app.test/login",
        } as never);

        expect(mockRedirect).toHaveBeenCalledTimes(1);
        expect(response).toEqual({ type: "redirect", url: "https://app.test/dashboard" });
    });

    it("continues when access is allowed", async () => {
        mockGetToken.mockResolvedValue({ sub: "user-id" });

        const response = await proxy({
            nextUrl: { pathname: "/dashboard" },
            url: "https://app.test/dashboard",
        } as never);

        expect(mockNext).toHaveBeenCalledTimes(1);
        expect(response).toEqual({ type: "next" });
    });

    it("exports expected route matcher config", () => {
        expect(config.matcher).toEqual(["/dashboard/:path*", "/decks/:path*", "/login"]);
    });
});
