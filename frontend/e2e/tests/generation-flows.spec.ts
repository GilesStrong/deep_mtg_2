import { expect, test, type Page } from "@playwright/test";

import {
    captureGenerationRequest,
    mockAuth,
    mockBuildStatus,
    mockDeckDetail,
    mockDeckListing,
    mockGenerationResponse,
    mockRemainingQuota,
    mockSetCodes,
    type DeckDetail,
    type DeckSummary,
} from "../helpers/network-mocks";

const DECK_ID = "deck-e2e-001";

const deckListing: DeckSummary[] = [
    {
        id: DECK_ID,
        name: "Izzet Spells",
        short_summary: "Spell-heavy tempo deck",
        set_codes: ["DMU", "WOE"],
        tags: ["Tempo"],
        date_updated: "2026-02-01T10:00:00.000Z",
        generation_status: "COMPLETED",
        generation_task_id: null,
    },
];

const deckDetail: DeckDetail = {
    id: DECK_ID,
    name: "Izzet Spells",
    short_summary: "Spell-heavy tempo deck",
    full_summary: "A red-blue spell deck for E2E validation.",
    set_codes: ["DMU", "WOE"],
    date_updated: "2026-02-01T10:00:00.000Z",
    creation_status: "COMPLETED",
    cards: [
        [
            2,
            {
                id: "card-1",
                name: "Lightning Strike",
                text: "Lightning Strike deals 3 damage to any target.",
                llm_summary: null,
                types: ["Instant"],
                subtypes: [],
                supertypes: [],
                set_codes: ["DMU"],
                rarity: "Common",
                converted_mana_cost: 2,
                mana_cost_colorless: 1,
                mana_cost_white: 0,
                mana_cost_blue: 0,
                mana_cost_black: 0,
                mana_cost_red: 1,
                mana_cost_green: 0,
                power: null,
                toughness: null,
                colors: ["R"],
                keywords: [],
            },
        ],
    ],
};

const assertDeckIdAbsent = (payload: Record<string, unknown>) => {
    expect(Object.prototype.hasOwnProperty.call(payload, "deck_id")).toBe(false);
};

const assertDeckIdPresent = (payload: Record<string, unknown>, deckId: string) => {
    expect(Object.prototype.hasOwnProperty.call(payload, "deck_id")).toBe(true);
    expect(payload.deck_id).toBe(deckId);
};

const setupCommonApiMocks = async (page: Page) => {
    await mockDeckListing(page, deckListing);
    await mockDeckDetail(page, deckDetail);
    await mockSetCodes(page, ["DMU", "WOE"]);
    await mockRemainingQuota(page, 3);
};

test("redirects unauthenticated users to login for protected routes", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("button", { name: "Sign in with Google" })).toBeVisible();
});

test("main page -> generate -> submit excludes deck_id", async ({ page }) => {
    await mockAuth(page);
    await setupCommonApiMocks(page);
    await mockGenerationResponse(page, { task_id: "task-flow-1" });
    await mockBuildStatus(page, "task-flow-1", DECK_ID, "COMPLETED");

    await page.goto("/");
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.getByRole("button", { name: "Generate Deck" }).click();
    await expect(page).toHaveURL(/\/decks\/generate$/);

    await page.getByLabel("Prompt").fill("Build an Izzet spells deck for best-of-one ladder.");
    const generationRequest = captureGenerationRequest(page);
    await page.getByRole("button", { name: "Submit Generation Task" }).click();

    const payload = (await generationRequest).postDataJSON() as Record<string, unknown>;
    assertDeckIdAbsent(payload);

    await expect(page).toHaveURL(new RegExp(`/decks/${DECK_ID}$`), { timeout: 15_000 });
});

test("deck detail -> regenerate -> submit includes inspected deck_id", async ({ page }) => {
    await mockAuth(page);
    await setupCommonApiMocks(page);
    await mockGenerationResponse(page, { task_id: "task-flow-2" });
    await mockBuildStatus(page, "task-flow-2", DECK_ID, "COMPLETED");

    await page.goto(`/decks/${DECK_ID}`);
    await expect(page.getByRole("heading", { name: "Deck Details" })).toBeVisible();

    await page.getByRole("button", { name: "Regenerate" }).click();
    await expect(page).toHaveURL(new RegExp(`/decks/generate\\?deckId=${DECK_ID}$`));

    await page.getByLabel("Prompt").fill("Regenerate with more instant-speed interaction.");
    const generationRequest = captureGenerationRequest(page);
    await page.getByRole("button", { name: "Submit Generation Task" }).click();

    const payload = (await generationRequest).postDataJSON() as Record<string, unknown>;
    assertDeckIdPresent(payload, DECK_ID);

    await expect(page).toHaveURL(new RegExp(`/decks/${DECK_ID}$`), { timeout: 15_000 });
});

test("deck detail -> regenerate -> dashboard -> generate -> submit excludes deck_id", async ({ page }) => {
    await mockAuth(page);
    await setupCommonApiMocks(page);
    await mockGenerationResponse(page, { task_id: "task-flow-3" });
    await mockBuildStatus(page, "task-flow-3", DECK_ID, "COMPLETED");

    await page.goto(`/decks/${DECK_ID}`);
    await expect(page.getByRole("heading", { name: "Deck Details" })).toBeVisible();

    await page.getByRole("button", { name: "Regenerate" }).click();
    await expect(page).toHaveURL(new RegExp(`/decks/generate\\?deckId=${DECK_ID}$`));

    await page.getByRole("button", { name: "Back to Decks" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.getByRole("button", { name: "Generate Deck" }).click();
    await expect(page).toHaveURL(/\/decks\/generate$/);

    await page.getByLabel("Prompt").fill("Generate a new deck unrelated to the previous one.");
    const generationRequest = captureGenerationRequest(page);
    await page.getByRole("button", { name: "Submit Generation Task" }).click();

    const payload = (await generationRequest).postDataJSON() as Record<string, unknown>;
    assertDeckIdAbsent(payload);

    await expect(page).toHaveURL(new RegExp(`/decks/${DECK_ID}$`), { timeout: 15_000 });
});
