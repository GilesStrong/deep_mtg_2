import { NextRequest, NextResponse } from "next/server";

const BACKEND_INTERNAL_URL = process.env.BACKEND_INTERNAL_URL ?? "http://web:8000";
const ACCESS_TOKEN_COOKIE = "backend_access_token";
const REFRESH_TOKEN_COOKIE = "backend_refresh_token";

const getCookieSecurity = () => ({
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
});

export async function POST(request: NextRequest): Promise<NextResponse> {
    let payload: unknown;
    try {
        payload = await request.json();
    } catch {
        return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
    }

    const response = await fetch(`${BACKEND_INTERNAL_URL}/api/app/token/exchange`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "User-Agent": request.headers.get("user-agent") ?? "",
            "X-Forwarded-For": request.headers.get("x-forwarded-for") ?? "",
        },
        body: JSON.stringify(payload),
        cache: "no-store",
    });

    let data: { access_token?: string; refresh_token?: string; detail?: string };
    try {
        data = (await response.json()) as { access_token?: string; refresh_token?: string; detail?: string };
    } catch {
        data = {};
    }

    if (!response.ok || !data.access_token || !data.refresh_token) {
        return NextResponse.json(
            { detail: data.detail ?? "Failed to exchange Google token" },
            { status: response.status || 500 },
        );
    }

    const nextResponse = NextResponse.json({ ok: true }, { status: 200 });
    const security = getCookieSecurity();

    nextResponse.cookies.set(ACCESS_TOKEN_COOKIE, data.access_token, security);
    nextResponse.cookies.set(REFRESH_TOKEN_COOKIE, data.refresh_token, security);

    return nextResponse;
}
