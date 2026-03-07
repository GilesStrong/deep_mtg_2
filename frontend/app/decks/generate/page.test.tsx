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

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { mockUseSession, mockUseRouter, mockUseSearchParams, mockBackendFetch, mockGetAvatarUrlFromSession } = vi.hoisted(() => ({
    mockUseSession: vi.fn(),
    mockUseRouter: vi.fn(),
    mockUseSearchParams: vi.fn(),
    mockBackendFetch: vi.fn(),
    mockGetAvatarUrlFromSession: vi.fn(),
}));

vi.mock("next-auth/react", () => ({
    useSession: mockUseSession,
    signOut: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useRouter: mockUseRouter,
    useSearchParams: mockUseSearchParams,
}));

vi.mock("@/lib/backend-auth", () => ({
    backendFetch: mockBackendFetch,
    clearBackendTokens: vi.fn(),
}));

vi.mock("@/lib/avatar", () => ({
    getAvatarUrlFromSession: mockGetAvatarUrlFromSession,
}));

import GenerateDeckPage from "@/app/decks/generate/page";

const mockJsonResponse = (data: unknown): Response =>
({
    ok: true,
    status: 200,
    json: vi.fn().mockResolvedValue(data),
    text: vi.fn().mockResolvedValue(JSON.stringify(data)),
} as unknown as Response);

const mockFailedResponse = (errorBody: unknown, status = 400): Response =>
({
    ok: false,
    status,
    json: vi.fn().mockResolvedValue(errorBody),
    text: vi.fn().mockResolvedValue(JSON.stringify(errorBody)),
} as unknown as Response);

describe("GenerateDeckPage", () => {
    const push = vi.fn();
    const replace = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();

        mockUseSession.mockReturnValue({
            data: {
                user: {
                    name: "Deck Builder",
                    email: "builder@test.dev",
                    googleAuthToken: "google-token",
                },
            },
        });
        mockUseRouter.mockReturnValue({ push, replace });
        mockUseSearchParams.mockReturnValue({
            get: () => null,
        });
        mockGetAvatarUrlFromSession.mockReturnValue("https://images.test/avatar.png");
    });

    afterEach(() => {
        cleanup();
    });

    it("submits generation payload with prompt and selected set codes", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/deck/daily_theme/") {
                return mockJsonResponse("Today's spellslinger theme");
            }

            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["BRO", "ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 3 });
            }

            if (url === "/api/app/ai/deck/" && init?.method === "POST") {
                return mockJsonResponse({ task_id: "task-1" });
            }

            if (url === "/api/app/ai/deck/build_status/task-1/") {
                return mockJsonResponse({ status: "IN_PROGRESS", deck_id: "deck-1" });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(await screen.findByText("Remaining builds today: 3")).toBeInTheDocument();

        const promptInput = screen.getByLabelText("Prompt");
        await user.type(promptInput, "Blue red spells with cheap interaction");
        await user.click(screen.getByRole("button", { name: "Submit Generation Task" }));

        await waitFor(() => {
            const postCall = mockBackendFetch.mock.calls.find(
                (call) => call[1] === "/api/app/ai/deck/" && call[2]?.method === "POST",
            );
            expect(postCall).toBeTruthy();

            const payload = JSON.parse(String(postCall?.[2]?.body)) as { prompt: string; set_codes: string[] };
            expect(payload.prompt).toBe("Blue red spells with cheap interaction");
            expect(payload.set_codes).toEqual(["BRO", "ONE"]);
        });
    });

    it("disables submit when remaining quota is zero", async () => {
        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/deck/daily_theme/") {
                return mockJsonResponse("Today's spellslinger theme");
            }

            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 0 });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(await screen.findByText("Remaining builds today: 0")).toBeInTheDocument();
        expect(
            screen.getByText("You have no remaining builds for today. Generation will be available again after midnight."),
        ).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Submit Generation Task" })).toBeDisabled();
    });

    it("shows prompt length counter and enables submit only within valid prompt length", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/deck/daily_theme/") {
                return mockJsonResponse("Today's spellslinger theme");
            }

            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 2 });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(await screen.findByText("Remaining builds today: 2")).toBeInTheDocument();
        expect(screen.getByText("0/3000")).toBeInTheDocument();

        const promptInput = screen.getByLabelText("Prompt");
        const submitButton = screen.getByRole("button", { name: "Submit Generation Task" });

        await user.type(promptInput, "short prompt");
        expect(screen.getByText("12/3000")).toBeInTheDocument();
        expect(submitButton).toBeDisabled();

        await user.clear(promptInput);
        await user.type(promptInput, "a".repeat(20));
        expect(screen.getByText("20/3000")).toBeInTheDocument();
        expect(submitButton).toBeEnabled();
    });

    it("disables submit when prompt length exceeds max", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/deck/daily_theme/") {
                return mockJsonResponse("Today's spellslinger theme");
            }

            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 2 });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(await screen.findByText("Remaining builds today: 2")).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText("Prompt"), {
            target: { value: "a".repeat(3001) },
        });

        expect(screen.getByText("3001/3000")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Submit Generation Task" })).toBeDisabled();
    });

    it("redirects to clean generate route when deckId marker is missing", async () => {
        mockUseSearchParams.mockReturnValue({
            get: (key: string) => (key === "deckId" ? "deck-1" : null),
        });

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/deck/daily_theme/") {
                return mockJsonResponse("Today's spellslinger theme");
            }

            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 1 });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        sessionStorage.removeItem("deep-mtg.regenerate-nav");

        render(<GenerateDeckPage />);

        await waitFor(() => {
            expect(replace).toHaveBeenCalledWith("/decks/generate");
        });
    });

    it("shows API error message when generation request fails", async () => {
        const user = userEvent.setup();

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/deck/daily_theme/") {
                return mockJsonResponse("Today's spellslinger theme");
            }

            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["BRO"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 2 });
            }

            if (url === "/api/app/ai/deck/" && init?.method === "POST") {
                return mockFailedResponse({ detail: "Prompt failed safety checks" });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(await screen.findByText("Remaining builds today: 2")).toBeInTheDocument();

        await user.type(screen.getByLabelText("Prompt"), "Build me a legal deck with forbidden card names to trigger validation.");
        await user.click(screen.getByRole("button", { name: "Submit Generation Task" }));

        expect(await screen.findByText("Prompt failed safety checks")).toBeInTheDocument();
    });

    it("shows toast when regeneration is blocked by in-progress generation", async () => {
        const user = userEvent.setup();

        mockUseSearchParams.mockReturnValue({
            get: (key: string) => (key === "deckId" ? "deck-1" : null),
        });

        sessionStorage.setItem(
            "deep-mtg.regenerate-nav",
            JSON.stringify({ deckId: "deck-1", createdAt: Date.now() })
        );

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["BRO", "ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 2 });
            }

            if (url === "/api/app/cards/deck/deck-1/") {
                return mockJsonResponse({ id: "deck-1", name: "Azorius Control" });
            }

            if (url === "/api/app/ai/deck/" && init?.method === "POST") {
                return mockFailedResponse({ detail: "Deck cannot be regenerated while generation is in progress" }, 409);
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(await screen.findByText("Target deck: Azorius Control")).toBeInTheDocument();
        await user.type(screen.getByLabelText("Prompt"), "Blue white control deck with sweepers and card advantage");
        await user.click(screen.getByRole("button", { name: "Submit Generation Task" }));

        expect(await screen.findByRole("status")).toHaveTextContent(
            "Deck cannot be regenerated while generation is in progress"
        );
    });

    it("shows regeneration target deck name instead of deck id", async () => {
        const user = userEvent.setup();

        mockUseSearchParams.mockReturnValue({
            get: (key: string) => (key === "deckId" ? "deck-1" : null),
        });

        sessionStorage.setItem(
            "deep-mtg.regenerate-nav",
            JSON.stringify({ deckId: "deck-1", createdAt: Date.now() })
        );

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["BRO", "ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 2 });
            }

            if (url === "/api/app/cards/deck/deck-1/") {
                return mockJsonResponse({ id: "deck-1", name: "Azorius Control" });
            }

            if (url === "/api/app/ai/deck/" && init?.method === "POST") {
                return mockJsonResponse({ task_id: "task-regen-1" });
            }

            if (url === "/api/app/ai/deck/build_status/task-regen-1/") {
                return mockJsonResponse({ status: "IN_PROGRESS", deck_id: "deck-1" });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(await screen.findByText("Target deck: Azorius Control")).toBeInTheDocument();

        await user.type(screen.getByLabelText("Prompt"), "Blue white control deck with sweepers and card advantage");
        await user.click(screen.getByRole("button", { name: "Submit Generation Task" }));

        await waitFor(() => {
            const postCall = mockBackendFetch.mock.calls.find(
                (call) => call[1] === "/api/app/ai/deck/" && call[2]?.method === "POST"
            );
            expect(postCall).toBeTruthy();

            const payload = JSON.parse(String(postCall?.[2]?.body)) as {
                prompt: string;
                set_codes: string[];
                deck_id?: string;
            };
            expect(payload.deck_id).toBe("deck-1");
        });

        expect(screen.queryByText(/Today's theme:/)).not.toBeInTheDocument();
    });

    it("prefills prompt from theme query param and submits it", async () => {
        const user = userEvent.setup();
        const themePrompt = "Build around sacrificing artifacts for recurring value and token generation.";

        mockUseSearchParams.mockReturnValue({
            get: (key: string) => (key === "theme" ? themePrompt : null),
        });

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string, init?: RequestInit) => {
            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["BRO", "ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 3 });
            }

            if (url === "/api/app/ai/deck/" && init?.method === "POST") {
                return mockJsonResponse({ task_id: "task-theme-1" });
            }

            if (url === "/api/app/ai/deck/build_status/task-theme-1/") {
                return mockJsonResponse({ status: "IN_PROGRESS", deck_id: "deck-1" });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(await screen.findByText("Remaining builds today: 3")).toBeInTheDocument();
        expect(screen.getByLabelText("Prompt")).toHaveValue(themePrompt);

        await user.click(screen.getByRole("button", { name: "Submit Generation Task" }));

        await waitFor(() => {
            const postCall = mockBackendFetch.mock.calls.find(
                (call) => call[1] === "/api/app/ai/deck/" && call[2]?.method === "POST",
            );
            expect(postCall).toBeTruthy();

            const payload = JSON.parse(String(postCall?.[2]?.body)) as { prompt: string; set_codes: string[] };
            expect(payload.prompt).toBe(themePrompt);
            expect(payload.set_codes).toEqual(["BRO", "ONE"]);
        });
    });

    it("shows daily theme and fills prompt when clicking generate this deck", async () => {
        const user = userEvent.setup();
        const dailyTheme = "Artifacts are sacrificed for value and recurred from the graveyard.";

        mockBackendFetch.mockImplementation(async (_session: unknown, url: string) => {
            if (url === "/api/app/cards/deck/daily_theme/") {
                return mockJsonResponse(dailyTheme);
            }

            if (url === "/api/app/cards/card/set_codes/") {
                return mockJsonResponse({ set_codes: ["BRO", "ONE"] });
            }

            if (url === "/api/app/ai/deck/remaining_quota/") {
                return mockJsonResponse({ remaining: 3 });
            }

            throw new Error(`Unexpected backend URL in test: ${url}`);
        });

        render(<GenerateDeckPage />);

        expect(
            await screen.findByText((_, element) => {
                const text = element?.textContent?.replace(/\s+/g, " ").trim();
                return text === `Today's theme: ${dailyTheme}`;
            })
        ).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Generate this deck" }));

        expect(screen.getByLabelText("Prompt")).toHaveValue(dailyTheme);
    });
});
