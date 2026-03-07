/*
Copyright 2026 Giles Strong

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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
    text: vi.fn().mockResolvedValue(""),
} as unknown as Response);

const mockFailedResponse = (status: number, body: unknown): Response =>
({
    ok: false,
    status,
    json: vi.fn().mockResolvedValue(body),
    text: vi.fn().mockResolvedValue(JSON.stringify(body)),
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
                    tags: ["Control", "Midrange"],
                    date_updated: "2026-02-01T10:00:00.000Z",
                    creation_status: "COMPLETED",
                    cards: [
                        {
                            quantity: 2,
                            role: "Primary Engine",
                            importance: "Critical",
                            card_info: {
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
                                tags: ["Control", "Removal"],
                            },
                            possible_replacements: [
                                {
                                    id: "card-2",
                                    name: "Day of Judgment",
                                    text: "Destroy all creatures.",
                                    llm_summary: "Lower-ceiling board wipe.",
                                    types: ["Sorcery"],
                                    subtypes: [],
                                    supertypes: [],
                                    set_codes: ["M11"],
                                    rarity: "Rare",
                                    converted_mana_cost: 4,
                                    mana_cost_colorless: 2,
                                    mana_cost_white: 2,
                                    mana_cost_blue: 0,
                                    mana_cost_black: 0,
                                    mana_cost_red: 0,
                                    mana_cost_green: 0,
                                    power: null,
                                    toughness: null,
                                    colors: ["W"],
                                    keywords: [],
                                    tags: ["Replacement"],
                                },
                            ],
                        },
                        {
                            quantity: 1,
                            role: "Primary Engine",
                            importance: "Generic",
                            card_info: {
                                id: "card-3",
                                name: "Silver Scrutiny",
                                text: "You may cast this spell as though it had flash if X is 3 or less.",
                                llm_summary: null,
                                types: ["Sorcery"],
                                subtypes: [],
                                supertypes: [],
                                set_codes: ["BRO"],
                                rarity: "Rare",
                                converted_mana_cost: 3,
                                mana_cost_colorless: 2,
                                mana_cost_white: 0,
                                mana_cost_blue: 1,
                                mana_cost_black: 0,
                                mana_cost_red: 0,
                                mana_cost_green: 0,
                                power: null,
                                toughness: null,
                                colors: ["U"],
                                keywords: [],
                                tags: ["Draw"],
                            },
                            possible_replacements: [],
                        },
                        {
                            quantity: 1,
                            role: "Support",
                            importance: "Functional",
                            card_info: {
                                id: "card-4",
                                name: "Make Disappear",
                                text: "Counter target spell unless its controller pays {2}.",
                                llm_summary: null,
                                types: ["Instant"],
                                subtypes: [],
                                supertypes: [],
                                set_codes: ["SNC"],
                                rarity: "Common",
                                converted_mana_cost: 2,
                                mana_cost_colorless: 1,
                                mana_cost_white: 0,
                                mana_cost_blue: 1,
                                mana_cost_black: 0,
                                mana_cost_red: 0,
                                mana_cost_green: 0,
                                power: null,
                                toughness: null,
                                colors: ["U"],
                                keywords: [],
                                tags: ["Interaction"],
                            },
                            possible_replacements: [],
                        },
                        {
                            quantity: 24,
                            role: "Land",
                            importance: "Generic",
                            card_info: {
                                id: "card-5",
                                name: "Island",
                                text: "({T}: Add {U}.)",
                                llm_summary: null,
                                types: ["Land"],
                                subtypes: ["Island"],
                                supertypes: ["Basic"],
                                set_codes: ["FDN"],
                                rarity: "Common",
                                converted_mana_cost: 0,
                                mana_cost_colorless: 0,
                                mana_cost_white: 0,
                                mana_cost_blue: 0,
                                mana_cost_black: 0,
                                mana_cost_red: 0,
                                mana_cost_green: 0,
                                power: null,
                                toughness: null,
                                colors: [],
                                keywords: [],
                                tags: ["Land"],
                            },
                            possible_replacements: [],
                        },
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
        expect(screen.getByText("Tags: Control, Midrange")).toBeInTheDocument();

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

    it("navigates to card search from deck details", async () => {
        const user = userEvent.setup();

        render(<DeckPage />);
        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Search Cards" }));

        expect(push).toHaveBeenCalledWith("/cards/search?deckId=deck-1");
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

    it("shows card tags as a list when card info is expanded", async () => {
        const user = userEvent.setup();

        render(<DeckPage />);
        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: /Sunfall/i }));

        expect(screen.getByText("Tags:")).toBeInTheDocument();
        const tagsList = screen.getByRole("list");
        expect(tagsList).toBeInTheDocument();
        expect(within(tagsList).getByText("Control")).toBeInTheDocument();
        expect(within(tagsList).getByText("Removal")).toBeInTheDocument();
    });

    it("shows toast when save is blocked by in-progress generation", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/deck/deck-1/full/") {
                return mockJsonResponse({
                    id: "deck-1",
                    name: "Azorius Control",
                    short_summary: "Control shell",
                    full_summary: "Long summary",
                    set_codes: ["ONE"],
                    tags: [],
                    date_updated: "2026-02-01T10:00:00.000Z",
                    creation_status: "COMPLETED",
                    cards: [],
                });
            }

            if (url === "/api/app/cards/deck/deck-1/" && init?.method === "PATCH") {
                return mockFailedResponse(409, { detail: "Deck cannot be edited while generation is in progress" });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<DeckPage />);
        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        const nameInput = screen.getByLabelText("Name");
        await user.clear(nameInput);
        await user.type(nameInput, "Azorius Control Updated");
        await user.click(screen.getByRole("button", { name: "Save Deck Details" }));

        expect(await screen.findByRole("status")).toHaveTextContent(
            "Deck cannot be edited while generation is in progress"
        );
    });

    it("disables deck alterations while build is in a pollable in-progress status", async () => {
        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/deck/deck-1/full/") {
                return mockJsonResponse({
                    id: "deck-1",
                    name: "Locked Deck",
                    short_summary: "Locked",
                    full_summary: "Locked during generation",
                    set_codes: ["FDN"],
                    tags: [],
                    date_updated: "2026-02-01T10:00:00.000Z",
                    creation_status: "BUILDING_DECK",
                    cards: [],
                });
            }

            if (url === "/api/app/cards/deck/deck-1/" && init?.method === "PATCH") {
                return mockJsonResponse({});
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<DeckPage />);
        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        expect(screen.getByRole("button", { name: "Search Cards" })).toBeDisabled();
        expect(screen.getByRole("button", { name: "Regenerate" })).toBeDisabled();
        expect(screen.getByRole("button", { name: "Delete Deck" })).toBeDisabled();
        expect(screen.getByRole("button", { name: "Save Deck Details" })).toBeDisabled();

        expect(screen.getByLabelText("Name")).toBeDisabled();
        expect(screen.getByLabelText("Short Description")).toBeDisabled();
        expect(screen.getByLabelText("Long Description")).toBeDisabled();
    });

    it("shows role grouping and card importance in uncollapsed card rows", async () => {
        render(<DeckPage />);

        expect(await screen.findByText("Deck Details")).toBeInTheDocument();
        expect(screen.getByText("Primary Engine")).toBeInTheDocument();
        expect(screen.getByText("Importance: Critical")).toBeInTheDocument();
    });

    it("orders role groups and card importance descending within groups", async () => {
        render(<DeckPage />);

        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        const roleHeadings = screen
            .getAllByRole("heading", { level: 3 })
            .map((heading) => heading.textContent)
            .filter((heading) => heading !== "Deck Details");
        expect(roleHeadings).toEqual(["Primary Engine", "Support", "Land"]);

        const primaryEngineSection = screen.getByRole("heading", { level: 3, name: "Primary Engine" }).parentElement;
        expect(primaryEngineSection).toBeTruthy();

        const primaryEngineImportanceLabels = within(primaryEngineSection as HTMLElement).getAllByText(/Importance:/i);
        expect(primaryEngineImportanceLabels[0]).toHaveTextContent("Importance: Critical");
        expect(primaryEngineImportanceLabels[1]).toHaveTextContent("Importance: Generic");
    });

    it("opens and closes replacements modal by overlay click and Escape", async () => {
        const user = userEvent.setup();

        render(<DeckPage />);
        expect(await screen.findByText("Deck Details")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: /View replacements/i }));

        expect(screen.getByRole("dialog", { name: /Replacement cards for Sunfall/i })).toBeInTheDocument();
        expect(screen.getByText("Day of Judgment")).toBeInTheDocument();

        await user.click(screen.getByText("Replacement Cards"));
        expect(screen.getByRole("dialog", { name: /Replacement cards for Sunfall/i })).toBeInTheDocument();

        await user.keyboard("{Escape}");
        await waitFor(() => {
            expect(screen.queryByRole("dialog", { name: /Replacement cards for Sunfall/i })).not.toBeInTheDocument();
        });

        await user.click(screen.getByRole("button", { name: /View replacements/i }));
        await user.click(screen.getByRole("dialog", { name: /Replacement cards for Sunfall/i }).parentElement as HTMLElement);
        await waitFor(() => {
            expect(screen.queryByRole("dialog", { name: /Replacement cards for Sunfall/i })).not.toBeInTheDocument();
        });
    });
});
