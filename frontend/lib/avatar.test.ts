import { describe, expect, it } from "vitest";

import { getAvatarUrlFromSession } from "@/lib/avatar";

describe("getAvatarUrlFromSession", () => {
    it("returns session image when present", () => {
        const url = getAvatarUrlFromSession({
            user: {
                image: "https://images.test/user.png",
            },
        } as never);

        expect(url).toBe("https://images.test/user.png");
    });

    it("returns empty string for missing values", () => {
        expect(getAvatarUrlFromSession(null)).toBe("");
        expect(
            getAvatarUrlFromSession({
                user: { image: "" },
            } as never),
        ).toBe("");
    });
});
