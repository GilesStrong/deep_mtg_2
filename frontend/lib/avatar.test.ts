import { describe, expect, it } from "vitest";

import { getAvatarUrlFromSession } from "@/lib/avatar";

const toBase64Url = (value: string): string =>
    btoa(value).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

const makeGoogleIdToken = (claims: Record<string, unknown>): string => {
    const header = toBase64Url(JSON.stringify({ alg: "none", typ: "JWT" }));
    const payload = toBase64Url(JSON.stringify(claims));
    return `${header}.${payload}.sig`;
};

describe("getAvatarUrlFromSession", () => {
    it("returns session image when present", () => {
        const url = getAvatarUrlFromSession({
            user: {
                image: "https://images.test/user.png",
                googleAuthToken: makeGoogleIdToken({ picture: "https://images.test/token.png" }),
            },
        } as never);

        expect(url).toBe("https://images.test/user.png");
    });

    it("falls back to picture claim from Google ID token", () => {
        const token = makeGoogleIdToken({ picture: "https://images.test/from-token.png" });

        const url = getAvatarUrlFromSession({
            user: {
                image: "",
                googleAuthToken: token,
            },
        } as never);

        expect(url).toBe("https://images.test/from-token.png");
    });

    it("returns empty string for invalid or missing values", () => {
        expect(getAvatarUrlFromSession(null)).toBe("");
        expect(
            getAvatarUrlFromSession({
                user: { googleAuthToken: "not-a-jwt", image: "" },
            } as never),
        ).toBe("");
    });
});
