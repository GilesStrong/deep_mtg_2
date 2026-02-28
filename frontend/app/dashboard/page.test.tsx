import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { mockUseSession, mockUseRouter, mockBackendFetch, mockGetAvatarUrlFromSession } = vi.hoisted(() => ({
    mockUseSession: vi.fn(),
    mockUseRouter: vi.fn(),
    mockBackendFetch: vi.fn(),
    mockGetAvatarUrlFromSession: vi.fn(),
}));

vi.mock("next-auth/react", () => ({
    useSession: mockUseSession,
    signOut: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: mockUseRouter,
}));

vi.mock("@/lib/backend-auth", () => ({
    backendFetch: mockBackendFetch,
    clearBackendTokens: vi.fn(),
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
});
