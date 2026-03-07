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

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
    mockUseSession,
    mockUseRouter,
    mockUseSearchParams,
    mockBackendFetch,
    mockGetAvatarUrlFromSession,
    mockSignOut,
    mockClearBackendTokens,
} = vi.hoisted(() => ({
    mockUseSession: vi.fn(),
    mockUseRouter: vi.fn(),
    mockUseSearchParams: vi.fn(),
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
    useSearchParams: mockUseSearchParams,
}));

vi.mock("@/lib/backend-auth", () => ({
    backendFetch: mockBackendFetch,
    clearBackendTokens: mockClearBackendTokens,
}));

vi.mock("@/lib/avatar", () => ({
    getAvatarUrlFromSession: mockGetAvatarUrlFromSession,
}));

import CardSearchPage from "@/app/cards/search/page";

const mockJsonResponse = (data: unknown): Response =>
({
    ok: true,
    status: 200,
    json: vi.fn().mockResolvedValue(data),
} as unknown as Response);

const mockTextErrorResponse = (status: number, detail: string): Response =>
({
    ok: false,
    status,
    text: vi.fn().mockResolvedValue(JSON.stringify({ detail })),
} as unknown as Response);

describe("CardSearchPage", () => {
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
        mockUseSearchParams.mockReturnValue({ get: vi.fn().mockReturnValue(null) });
        mockGetAvatarUrlFromSession.mockReturnValue("https://images.test/avatar.png");

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE", "DMU"] });
            }

            if (url === "/api/app/cards/card/tags/") {
                return mockJsonResponse({
                    tags: {
                        Strategy: {
                            Control: "Cards that are designed to manage the game state.",
                            Ramp: "Cards that accelerate mana production.",
                        },
                    },
                });
            }

            if (url === "/api/app/search/search/" && init?.method === "POST") {
                return mockJsonResponse({
                    cards: [
                        {
                            relevance_score: 0.3,
                            card_info: {
                                id: "card-2",
                                name: "Memory Deluge",
                                text: "Look at the top X cards of your library...",
                                llm_summary: null,
                                types: ["Instant"],
                                subtypes: [],
                                supertypes: [],
                                set_codes: ["MID"],
                                rarity: "Rare",
                                converted_mana_cost: 4,
                                mana_cost_colorless: 2,
                                mana_cost_white: 0,
                                mana_cost_blue: 2,
                                mana_cost_black: 0,
                                mana_cost_red: 0,
                                mana_cost_green: 0,
                                power: null,
                                toughness: null,
                                colors: ["U"],
                                keywords: ["Flashback"],
                                tags: ["Control"],
                            },
                        },
                        {
                            relevance_score: 0.8,
                            card_info: {
                                id: "card-1",
                                name: "Sunfall",
                                text: "Exile all creatures.",
                                llm_summary: "Board reset spell.",
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
                                tags: ["Control", "BoardWipe"],
                            },
                        },
                    ],
                });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("submits query with filters and renders expandable results", async () => {
        const user = userEvent.setup();

        render(<CardSearchPage />);

        expect(await screen.findByText("Card Search")).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Back to Deck" })).not.toBeInTheDocument();

        await user.type(screen.getByLabelText("Query"), "Find me cards that clear the board and stabilise early game");
        await user.click(screen.getByRole("button", { name: "White" }));
        await user.click(screen.getByRole("button", { name: "ONE" }));
        await user.click(screen.getByRole("button", { name: "Control" }));

        expect(screen.getByRole("button", { name: "Control" })).toHaveAttribute(
            "title",
            "Cards that are designed to manage the game state."
        );

        await user.click(screen.getByRole("button", { name: "Search Cards" }));

        expect(await screen.findByText("Sunfall")).toBeInTheDocument();
        expect(screen.getByText("Memory Deluge")).toBeInTheDocument();
        expect(screen.queryByText("0.8")).not.toBeInTheDocument();

        await waitFor(() => {
            const call = mockBackendFetch.mock.calls.find(
                (entry) => entry[1] === "/api/app/search/search/" && entry[2]?.method === "POST"
            );
            expect(call).toBeTruthy();
            const payload = JSON.parse(String(call?.[2]?.body)) as {
                query: string;
                colors: string[];
                set_codes: string[];
                tags: string[];
            };
            expect(payload.query).toBe("Find me cards that clear the board and stabilise early game");
            expect(payload.colors).toEqual(["W"]);
            expect(payload.set_codes).toEqual(["ONE"]);
            expect(payload.tags).toEqual(["Control"]);
        });

        await user.click(screen.getByRole("button", { name: /Sunfall/i }));

        expect(screen.getByText("Tags:")).toBeInTheDocument();
        expect(screen.getByRole("list")).toBeInTheDocument();
        expect(screen.getByText("BoardWipe")).toBeInTheDocument();
    });

    it("enforces query length constraints", async () => {
        const user = userEvent.setup();

        render(<CardSearchPage />);

        const searchButton = await screen.findByRole("button", { name: "Search Cards" });
        expect(searchButton).toBeDisabled();

        await user.type(screen.getByLabelText("Query"), "short query");
        expect(searchButton).toBeDisabled();

        await user.clear(screen.getByLabelText("Query"));
        await user.type(screen.getByLabelText("Query"), "This query has enough words to pass validation");

        expect(searchButton).toBeEnabled();
    });

    it("shows api error messages when search fails", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE"] });
            }

            if (url === "/api/app/cards/card/tags/") {
                return mockJsonResponse({
                    tags: {
                        Strategy: {
                            Control: "Cards that are designed to manage the game state.",
                        },
                    },
                });
            }

            if (url === "/api/app/search/search/" && init?.method === "POST") {
                return mockTextErrorResponse(429, "Too many card search attempts.");
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<CardSearchPage />);

        await user.type(screen.getByLabelText("Query"), "Find me cards that clear the board and stabilise early game");
        await user.click(await screen.findByRole("button", { name: "Search Cards" }));

        expect(await screen.findByText("Too many card search attempts.")).toBeInTheDocument();
    });

    it("shows back to deck button when deckId is provided", async () => {
        const user = userEvent.setup();

        mockUseSearchParams.mockReturnValue({
            get: vi.fn((key: string) => (key === "deckId" ? "deck-1" : null)),
        });

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE", "DMU"] });
            }

            if (url === "/api/app/cards/card/tags/") {
                return mockJsonResponse({
                    tags: {
                        Strategy: {
                            Control: "Cards that are designed to manage the game state.",
                            Ramp: "Cards that accelerate mana production.",
                        },
                    },
                });
            }

            if (url === "/api/app/cards/deck/deck-1/full/") {
                return mockJsonResponse({
                    short_summary: "Control deck focused on board wipes and card advantage",
                    set_codes: ["ONE"],
                    cards: [],
                });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<CardSearchPage />);

        expect(await screen.findByRole("button", { name: "Back to Deck" })).toBeInTheDocument();
        await user.click(screen.getByRole("button", { name: "Back to Deck" }));
        expect(push).toHaveBeenCalledWith("/decks/deck-1");
    });

    it("renders results when backend returns alternate payload keys", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE"] });
            }

            if (url === "/api/app/cards/card/tags/") {
                return mockJsonResponse({
                    tags: {
                        Strategy: {
                            Control: "Cards that are designed to manage the game state.",
                        },
                    },
                });
            }

            if (url === "/api/app/search/search/" && init?.method === "POST") {
                return mockJsonResponse({
                    results: [
                        {
                            score: "0.91",
                            card: {
                                id: 101,
                                name: "Temporary Lockdown",
                                text: "When Temporary Lockdown enters the battlefield...",
                                llm_summary: null,
                                types: ["Enchantment"],
                                subtypes: [],
                                supertypes: [],
                                set_codes: ["DMU"],
                                rarity: "Rare",
                                converted_mana_cost: 3,
                                mana_cost_colorless: 1,
                                mana_cost_white: 2,
                                mana_cost_blue: 0,
                                mana_cost_black: 0,
                                mana_cost_red: 0,
                                mana_cost_green: 0,
                                power: null,
                                toughness: null,
                                colors: ["W"],
                                keywords: [],
                                tags: ["Control"],
                            },
                        },
                    ],
                });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<CardSearchPage />);

        await user.type(screen.getByLabelText("Query"), "Find cards that tax opponents and protect early turns");
        await user.click(await screen.findByRole("button", { name: "Search Cards" }));

        expect(await screen.findByText("Temporary Lockdown")).toBeInTheDocument();
    });

    it("renders results when backend wraps payload under data.cards", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE"] });
            }

            if (url === "/api/app/cards/card/tags/") {
                return mockJsonResponse({
                    tags: {
                        Strategy: {
                            Control: "Cards that are designed to manage the game state.",
                        },
                    },
                });
            }

            if (url === "/api/app/search/search/" && init?.method === "POST") {
                return mockJsonResponse({
                    data: {
                        cards: [
                            {
                                relevance_score: 0.55,
                                card_info: {
                                    id: "card-55",
                                    name: "Depopulate",
                                    text: "Each player who controls a multicolored creature draws a card.",
                                    llm_summary: null,
                                    types: ["Sorcery"],
                                    subtypes: [],
                                    supertypes: [],
                                    set_codes: ["SNC"],
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
                                    tags: ["BoardWipe"],
                                },
                            },
                        ],
                    },
                });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<CardSearchPage />);

        await user.type(screen.getByLabelText("Query"), "Find white board wipes for stabilizing creature matchups");
        await user.click(await screen.findByRole("button", { name: "Search Cards" }));

        expect(await screen.findByText("Depopulate")).toBeInTheDocument();
    });

    it("renders results when card info is nested under payload alias", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE"] });
            }

            if (url === "/api/app/cards/card/tags/") {
                return mockJsonResponse({ tags: {} });
            }

            if (url === "/api/app/search/search/" && init?.method === "POST") {
                return mockJsonResponse({
                    cards: [
                        {
                            relevance_score: 0.42,
                            payload: {
                                id: "card-payload-1",
                                name: "Lay Down Arms",
                                text: "Exile target creature with mana value less than or equal to the number of Plains you control.",
                                llm_summary: null,
                                types: ["Sorcery"],
                                subtypes: [],
                                supertypes: [],
                                set_codes: ["BRO"],
                                rarity: "Uncommon",
                                converted_mana_cost: 1,
                                mana_cost_colorless: 0,
                                mana_cost_white: 1,
                                mana_cost_blue: 0,
                                mana_cost_black: 0,
                                mana_cost_red: 0,
                                mana_cost_green: 0,
                                power: null,
                                toughness: null,
                                colors: ["W"],
                                keywords: [],
                                tags: ["SpotRemoval"],
                            },
                        },
                    ],
                });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<CardSearchPage />);

        await user.type(screen.getByLabelText("Query"), "Find cheap white spot removal for creature-heavy matchups");
        await user.click(await screen.findByRole("button", { name: "Search Cards" }));

        expect(await screen.findByText("Lay Down Arms")).toBeInTheDocument();
    });

    it("prefills query and filters from source deck context", async () => {
        const user = userEvent.setup();

        mockUseSearchParams.mockReturnValue({
            get: vi.fn((key: string) => (key === "deckId" ? "deck-1" : null)),
        });

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE", "DMU"] });
            }

            if (url === "/api/app/cards/card/tags/") {
                return mockJsonResponse({
                    tags: {
                        Strategy: {
                            Control: "Cards that are designed to manage the game state.",
                            Ramp: "Cards that accelerate mana production.",
                        },
                    },
                });
            }

            if (url === "/api/app/cards/deck/deck-1/full/") {
                return mockJsonResponse({
                    short_summary: "Control deck focused on board wipes and card advantage",
                    set_codes: ["ONE"],
                    cards: [
                        [
                            2,
                            {
                                colors: ["W", "U"],
                                tags: ["Control"],
                                set_codes: ["DMU"],
                            },
                        ],
                    ],
                });
            }

            if (url === "/api/app/search/search/" && init?.method === "POST") {
                return mockJsonResponse({ cards: [] });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<CardSearchPage />);

        expect(await screen.findByDisplayValue("Control deck focused on board wipes and card advantage")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Search Cards" }));

        await waitFor(() => {
            const call = mockBackendFetch.mock.calls.find(
                (entry) => entry[1] === "/api/app/search/search/" && entry[2]?.method === "POST"
            );
            expect(call).toBeTruthy();

            const payload = JSON.parse(String(call?.[2]?.body)) as {
                query: string;
                set_codes: string[];
                colors: string[];
                tags: string[];
            };

            expect(payload.query).toBe("Control deck focused on board wipes and card advantage");
            expect(payload.set_codes.sort()).toEqual(["DMU", "ONE"]);
            expect(payload.colors.sort()).toEqual(["U", "W"]);
            expect(payload.tags).toEqual(["Control"]);
        });
    });

    it("only sends subtags when primary tags are selected in state", async () => {
        const user = userEvent.setup();

        mockUseSearchParams.mockReturnValue({
            get: vi.fn((key: string) => (key === "deckId" ? "deck-1" : null)),
        });

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE", "DMU"] });
            }

            if (url === "/api/app/cards/card/tags/") {
                return mockJsonResponse({
                    tags: {
                        Strategy: {
                            Control: "Cards that are designed to manage the game state.",
                            Ramp: "Cards that accelerate mana production.",
                        },
                    },
                });
            }

            if (url === "/api/app/cards/deck/deck-1/full/") {
                return mockJsonResponse({
                    short_summary: "Control shell with board wipes",
                    set_codes: ["ONE"],
                    cards: [
                        [
                            2,
                            {
                                colors: ["W"],
                                tags: ["Strategy", "Control"],
                                set_codes: ["ONE"],
                            },
                        ],
                    ],
                });
            }

            if (url === "/api/app/search/search/" && init?.method === "POST") {
                return mockJsonResponse({ cards: [] });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<CardSearchPage />);

        expect(await screen.findByDisplayValue("Control shell with board wipes")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Search Cards" }));

        await waitFor(() => {
            const call = mockBackendFetch.mock.calls.find(
                (entry) => entry[1] === "/api/app/search/search/" && entry[2]?.method === "POST"
            );
            expect(call).toBeTruthy();

            const payload = JSON.parse(String(call?.[2]?.body)) as {
                tags: string[];
            };

            expect(payload.tags).toEqual(["Control"]);
            expect(payload.tags).not.toContain("Strategy");
        });
    });
});
