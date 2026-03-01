import { expect, test } from "@playwright/test";

import {
    captureDeleteConfirmationRequest,
    mockAccountExport,
    mockAuth,
    mockDeleteConfirm,
    mockDeleteRequest,
} from "../helpers/network-mocks";

const exportPayload = {
    exported_at: "2026-03-01T00:00:00.000Z",
    user: {
        id: "00000000-0000-0000-0000-000000000001",
        google_id: "gid-e2e",
        verified: true,
        warning_count: 0,
    },
    decks: [],
    refresh_tokens: [],
};

test("account page export triggers mocked backend download flow", async ({ page }) => {
    await mockAuth(page);
    await mockAccountExport(page, exportPayload);

    await page.goto("/dashboard/account");
    await expect(page.getByRole("heading", { name: "Account" })).toBeVisible();

    await page.getByRole("button", { name: "Export My Data" }).click();

    await expect(page.getByText("Account data export downloaded.")).toBeVisible();
});

test("account page deletion uses two-step flow with confirmation token", async ({ page }) => {
    await mockAuth(page);
    await mockDeleteRequest(page, {
        confirmation_token: "e2e-confirm-token",
        expires_in_seconds: 900,
    });
    await mockDeleteConfirm(page);

    await page.goto("/dashboard/account");
    await expect(page.getByRole("button", { name: "Delete My Account" })).toBeDisabled();

    await page.getByRole("button", { name: "Step 1: Request Deletion" }).click();
    await expect(
        page.getByText("Deletion requested. Confirm within 900 seconds to permanently delete your account.")
    ).toBeVisible();

    const deleteRequest = captureDeleteConfirmationRequest(page);
    await page.getByRole("button", { name: "Delete My Account" }).click();

    const payload = (await deleteRequest).postDataJSON() as { confirmation_token?: string };
    expect(payload.confirmation_token).toBe("e2e-confirm-token");

    await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });
});
