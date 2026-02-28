import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { mockUseSession, mockUseRouter, mockUseParams, mockBackendFetch, mockGetAvatarUrlFromSession } = vi.hoisted(() => ({
    mockUseSession: vi.fn(),
    mockUseRouter: vi.fn(),
    mockUseParams: vi.fn(),
    mockBackendFetch: vi.fn(),
    mockGetAvatarUrlFromSession: vi.fn(),
}));

vi.mock("next-auth/react", () => ({
    useSession: mockUseSession,
    signOut: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: mockUseRouter,
    useParams: mockUseParams,
}));

vi.mock("@/lib/backend-auth", () => ({
    backendFetch: mockBackendFetch,
    clearBackendTokens: vi.fn(),
}));

vi.mock("@/lib/avatar", () => ({
    getAvatarUrlFromSession: mockGetAvatarUrlFromSession,
}));

import DeckPage from "@/app/decks/[deckId]/page";

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

describe("DeckPage", () => {
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
        });
        mockUseRouter.mockReturnValue({ push });
        mockUseParams.mockReturnValue({ deckId: "deck-1" });
        mockGetAvatarUrlFromSession.mockReturnValue("https://images.test/avatar.png");

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/deck/deck-1/full/") {
                return mockJsonResponse({
                    id: "deck-1",
                    name: "Azorius Control",
                    short_summary: "Control shell",
                    full_summary: "Long summary",
                    set_codes: ["ONE"],
                    date_updated: "2026-02-01T10:00:00.000Z",
                    creation_status: "COMPLETED",
                    cards: [
                        [2, {
                            id: "card-1",
                            name: "Sunfall",
                            text: "Exile all creatures.",
                            llm_summary: null,
                            types: ["Sorcery"],
                            subtypes: [],
                            supertypes: [],
                            set_codes: ["ONE"],
                            rarity: "Rare",
                            converted_mana_cost: 5,
                            mana_cost_colorless: 3,
                            mana_cost_white: 2,
                            mana_cost_blue: 0,
                            mana_cost_black: 0,
                            mana_cost_red: 0,
                            mana_cost_green: 0,
                            power: null,
                            toughness: null,
                            colors: ["W"],
                            keywords: [],
                        }],
                    ],
                });
            }

            if (url === "/api/app/cards/deck/deck-1/" && init?.method === "PATCH") {
                return mockJsonResponse({});
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });
    });

    afterEach(() => {
        cleanup();
        sessionStorage.clear();
    });

    it("loads deck details and saves changed fields", async () => {
        const user = userEvent.setup();

        render(<DeckPage />);
        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        const nameInput = screen.getByLabelText("Name");
        await user.clear(nameInput);
        await user.type(nameInput, "Azorius Control Updated");
        await user.click(screen.getByRole("button", { name: "Save Deck Details" }));

        await waitFor(() => {
            const patchCall = mockBackendFetch.mock.calls.find(
                (call) => call[1] === "/api/app/cards/deck/deck-1/" && call[2]?.method === "PATCH",
            );
            expect(patchCall).toBeTruthy();

            const payload = JSON.parse(String(patchCall?.[2]?.body)) as {
                name: string | null;
                short_summary: string | null;
                full_summary: string | null;
            };
            expect(payload.name).toBe("Azorius Control Updated");
            expect(payload.short_summary).toBeNull();
            expect(payload.full_summary).toBeNull();
        });
    });

    it("sets regenerate marker and navigates to regenerate flow", async () => {
        const user = userEvent.setup();

        render(<DeckPage />);
        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Regenerate" }));

        const markerRaw = sessionStorage.getItem("deep-mtg.regenerate-nav");
        expect(markerRaw).toBeTruthy();

        const marker = JSON.parse(String(markerRaw)) as { deckId: string | null; createdAt: number };
        expect(marker.deckId).toBe("deck-1");
        expect(typeof marker.createdAt).toBe("number");
        expect(push).toHaveBeenCalledWith("/decks/generate?deckId=deck-1");
    });

    it("shows not found state when deck fetch fails", async () => {
        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/deck/deck-1/full/") {
                return mockErrorResponse();
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<DeckPage />);

        expect(await screen.findByText("Deck not found")).toBeInTheDocument();
    });

    it("does not delete when confirmation is cancelled", async () => {
        const user = userEvent.setup();
        const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

        render(<DeckPage />);
        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Delete Deck" }));

        const deleteCall = mockBackendFetch.mock.calls.find(
            (call) => call[1] === "/api/app/cards/deck/deck-1/" && call[2]?.method === "DELETE",
        );
        expect(confirmSpy).toHaveBeenCalledTimes(1);
        expect(deleteCall).toBeUndefined();
        expect(push).not.toHaveBeenCalledWith("/dashboard");
    });
});
