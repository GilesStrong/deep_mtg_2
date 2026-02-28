import { beforeAll, describe, expect, it } from "vitest";

const toBase64Url = (value: string): string =>
    btoa(value).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

const makeGoogleIdToken = (claims: Record<string, unknown>): string => {
    const header = toBase64Url(JSON.stringify({ alg: "none", typ: "JWT" }));
    const payload = toBase64Url(JSON.stringify(claims));
    return `${header}.${payload}.sig`;
};

let authOptions: (typeof import("@/lib/auth"))["authOptions"];

beforeAll(async () => {
    process.env.GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID ?? "test-google-client-id";
    process.env.GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET ?? "test-google-client-secret";
    ({ authOptions } = await import("@/lib/auth"));
});

describe("authOptions callbacks", () => {
    it("redirect callback handles relative and same-origin URLs", async () => {
        expect(
            await authOptions.callbacks?.redirect?.({
                url: "/dashboard",
                baseUrl: "https://app.test",
            }),
        ).toBe("https://app.test/dashboard");

        expect(
            await authOptions.callbacks?.redirect?.({
                url: "https://app.test/decks",
                baseUrl: "https://app.test",
            }),
        ).toBe("https://app.test/decks");

        expect(
            await authOptions.callbacks?.redirect?.({
                url: "https://evil.test/phish",
                baseUrl: "https://app.test",
            }),
        ).toBe("https://app.test");
    });

    it("jwt callback stores Google token and decoded claims", async () => {
        const idToken = makeGoogleIdToken({
            picture: "https://images.test/pic.png",
            name: "Jace Beleren",
            email: "jace@test.dev",
        });

        const token = await authOptions.callbacks?.jwt?.({
            token: {},
            account: { id_token: idToken },
            profile: undefined,
        } as never);

        expect(token?.googleAuthToken).toBe(idToken);
        expect(token?.picture).toBe("https://images.test/pic.png");
        expect(token?.name).toBe("Jace Beleren");
        expect(token?.email).toBe("jace@test.dev");
    });

    it("session callback projects token values onto session.user", async () => {
        const session = await authOptions.callbacks?.session?.({
            session: { user: {} },
            token: {
                googleAuthToken: "token-123",
                picture: "https://images.test/user.png",
                name: "Teferi",
                email: "teferi@test.dev",
            },
        } as never);

        expect(session?.user?.googleAuthToken).toBe("token-123");
        expect(session?.user?.image).toBe("https://images.test/user.png");
        expect(session?.user?.name).toBe("Teferi");
        expect(session?.user?.email).toBe("teferi@test.dev");
    });
});
