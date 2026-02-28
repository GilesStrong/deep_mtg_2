import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { mockUseSession, mockSignOut, mockSessionProvider, mockClearBackendTokens, mockEnsureBackendTokens } = vi.hoisted(() => ({
    mockUseSession: vi.fn(),
    mockSignOut: vi.fn(),
    mockSessionProvider: vi.fn(),
    mockClearBackendTokens: vi.fn(),
    mockEnsureBackendTokens: vi.fn(),
}));

vi.mock("next-auth/react", () => ({
    useSession: mockUseSession,
    signOut: mockSignOut,
    SessionProvider: ({ children }: { children: React.ReactNode }) => {
        mockSessionProvider();
        return <div data-testid="session-provider">{children}</div>;
    },
}));

vi.mock("@/lib/backend-auth", () => ({
    clearBackendTokens: mockClearBackendTokens,
    ensureBackendTokens: mockEnsureBackendTokens,
}));

import { Providers } from "@/app/providers";

describe("Providers", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    it("clears backend tokens when user is not authenticated", async () => {
        mockUseSession.mockReturnValue({ data: null, status: "unauthenticated" });

        render(
            <Providers>
                <div>Child</div>
            </Providers>,
        );

        expect(screen.getByTestId("session-provider")).toBeInTheDocument();
        expect(screen.getByText("Child")).toBeInTheDocument();

        await waitFor(() => {
            expect(mockClearBackendTokens).toHaveBeenCalledTimes(1);
        });
        expect(mockEnsureBackendTokens).not.toHaveBeenCalled();
        expect(mockSignOut).not.toHaveBeenCalled();
    });

    it("syncs backend tokens when authenticated", async () => {
        const session = { user: { email: "builder@test.dev" } };
        mockUseSession.mockReturnValue({ data: session, status: "authenticated" });
        mockEnsureBackendTokens.mockResolvedValue(undefined);

        render(
            <Providers>
                <div>Child</div>
            </Providers>,
        );

        await waitFor(() => {
            expect(mockEnsureBackendTokens).toHaveBeenCalledWith(session);
        });
        expect(mockClearBackendTokens).not.toHaveBeenCalled();
        expect(mockSignOut).not.toHaveBeenCalled();
    });

    it("clears tokens and signs out with encoded error when sync fails", async () => {
        const session = { user: { email: "builder@test.dev" } };
        mockUseSession.mockReturnValue({ data: session, status: "authenticated" });
        mockEnsureBackendTokens.mockRejectedValue(new Error("Token exchange failed"));

        render(
            <Providers>
                <div>Child</div>
            </Providers>,
        );

        await waitFor(() => {
            expect(mockClearBackendTokens).toHaveBeenCalledTimes(1);
            expect(mockSignOut).toHaveBeenCalledWith({
                callbackUrl: "/login?error=Token%20exchange%20failed",
            });
        });
    });
});
