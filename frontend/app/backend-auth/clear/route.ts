import { NextResponse } from "next/server";

const ACCESS_TOKEN_COOKIE = "backend_access_token";
const REFRESH_TOKEN_COOKIE = "backend_refresh_token";

const getCookieSecurity = () => ({
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
});

export async function POST(): Promise<NextResponse> {
    const nextResponse = NextResponse.json({ ok: true }, { status: 200 });
    const security = getCookieSecurity();

    nextResponse.cookies.set(ACCESS_TOKEN_COOKIE, "", { ...security, maxAge: 0 });
    nextResponse.cookies.set(REFRESH_TOKEN_COOKIE, "", { ...security, maxAge: 0 });

    return nextResponse;
}
