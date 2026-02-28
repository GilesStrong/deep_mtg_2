import { describe, expect, it, vi } from "vitest";

const { mockNextAuth, mockAuthOptions, mockHandler } = vi.hoisted(() => ({
    mockNextAuth: vi.fn(),
    mockAuthOptions: { providers: ["mock-provider"] },
    mockHandler: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
    authOptions: mockAuthOptions,
}));

vi.mock("next-auth", () => ({
    default: mockNextAuth,
}));

const loadRouteModule = async () => {
    vi.resetModules();
    mockNextAuth.mockReturnValue(mockHandler);
    return import("@/app/api/auth/[...nextauth]/route");
};

describe("auth route handler exports", () => {
    it("builds handler with authOptions", async () => {
        await loadRouteModule();

        expect(mockNextAuth).toHaveBeenCalledTimes(1);
        expect(mockNextAuth).toHaveBeenCalledWith(mockAuthOptions);
    });

    it("exports GET and POST as the same NextAuth handler", async () => {
        const routeModule = await loadRouteModule();

        expect(routeModule.GET).toBe(mockHandler);
        expect(routeModule.POST).toBe(mockHandler);
    });
});
