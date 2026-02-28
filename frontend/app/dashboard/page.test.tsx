import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
    mockUseSession,
    mockUseRouter,
    mockBackendFetch,
    mockGetAvatarUrlFromSession,
    mockSignOut,
    mockClearBackendTokens,
} = vi.hoisted(() => ({
    mockUseSession: vi.fn(),
    mockUseRouter: vi.fn(),
    mockBackendFetch: vi.fn(),
    mockGetAvatarUrlFromSession: vi.fn(),
    mockSignOut: vi.fn(),
    mockClearBackendTokens: vi.fn(),
}));

vi.mock("next-auth/react", () => ({
    useSession: mockUseSession,
    signOut: mockSignOut,
}));

vi.mock("next/navigation", () => ({
    useRouter: mockUseRouter,
}));

vi.mock("@/lib/backend-auth", () => ({
    backendFetch: mockBackendFetch,
    clearBackendTokens: mockClearBackendTokens,
}));

vi.mock("@/lib/avatar", () => ({
    getAvatarUrlFromSession: mockGetAvatarUrlFromSession,
}));

import DashboardPage from "@/app/dashboard/page";

const mockJsonResponse = (data: unknown): Response =>
({
    ok: true,
    status: 200,
    json: vi.fn().mockResolvedValue(data),
} as unknown as Response);

const mockErrorResponse = (): Response =>
({
    ok: false,
    status: 500,
    json: vi.fn().mockResolvedValue({}),
} as unknown as Response);

describe("DashboardPage", () => {
    const push = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();

        mockUseSession.mockReturnValue({
            data: {
                user: {
                    name: "Deck Builder",
                    email: "builder@test.dev",
                },
            },
            status: "authenticated",
        });
        mockUseRouter.mockReturnValue({ push });
        mockGetAvatarUrlFromSession.mockReturnValue("https://images.test/avatar.png");

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE", "DMU"] });
            }

            if (url === "/api/app/cards/deck/") {
                return mockJsonResponse([
                    {
                        id: "deck-1",
                        name: "Izzet Spells",
                        short_summary: "Blue-red tempo",
                        set_codes: ["DMU"],
                        date_updated: "2026-02-01T10:00:00.000Z",
                        generation_status: null,
                        generation_task_id: null,
                    },
                    {
                        id: "deck-2",
                        name: "Mono White",
                        short_summary: "Aggro",
                        set_codes: ["ONE"],
                        date_updated: "2026-02-02T10:00:00.000Z",
                        generation_status: null,
                        generation_task_id: null,
                    },
                ]);
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("loads dashboard data and navigates to generate page", async () => {
        const user = userEvent.setup();

        render(<DashboardPage />);

        expect(await screen.findByText("Izzet Spells")).toBeInTheDocument();
        expect(screen.getByText("Mono White")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Generate Deck" }));
        expect(push).toHaveBeenCalledWith("/decks/generate");
    });

    it("filters decks by selected set code", async () => {
        const user = userEvent.setup();

        render(<DashboardPage />);
        expect(await screen.findByText("Izzet Spells")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "ONE" }));

        expect(screen.getByText("Mono White")).toBeInTheDocument();
        expect(screen.queryByText("Izzet Spells")).not.toBeInTheDocument();
        expect(screen.getByText("Filter active: 1 set code selected.")).toBeInTheDocument();
    });

    it("shows empty states when deck and set code requests fail", async () => {
        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/card/set_codes/" || url === "/api/app/cards/deck/") {
                return mockErrorResponse();
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<DashboardPage />);

        expect(await screen.findByText("No set codes available.")).toBeInTheDocument();
        expect(await screen.findByText("No decks found")).toBeInTheDocument();
        expect(screen.getByText("Create your first deck to get started.")).toBeInTheDocument();
    });

    it("clears tokens and signs out from the user menu", async () => {
        const user = userEvent.setup();

        render(<DashboardPage />);
        expect(await screen.findByText("Izzet Spells")).toBeInTheDocument();

        const avatarButton = document.querySelector("button.relative.h-10.w-10.rounded-full");
        expect(avatarButton).toBeTruthy();
        await user.click(avatarButton as HTMLElement);

        await user.click(await screen.findByText("Sign out"));

        expect(mockClearBackendTokens).toHaveBeenCalledTimes(1);
        expect(mockSignOut).toHaveBeenCalledWith({ callbackUrl: "/login" });
    });
});
