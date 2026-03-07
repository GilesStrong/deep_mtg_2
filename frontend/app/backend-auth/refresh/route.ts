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

import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";

const BACKEND_INTERNAL_URL = process.env.BACKEND_INTERNAL_URL ?? "http://web:8000";
const ACCESS_TOKEN_COOKIE = "backend_access_token";
const REFRESH_TOKEN_COOKIE = "backend_refresh_token";
const CSRF_COOKIE = "backend_csrf_token";

const getCookieSecurity = () => ({
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
});

export async function POST(request: NextRequest): Promise<NextResponse> {
    const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;
    if (!refreshToken) {
        return NextResponse.json({ detail: "Missing refresh token" }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_INTERNAL_URL}/api/app/token/refresh`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "User-Agent": request.headers.get("user-agent") ?? "",
            "X-Forwarded-For": request.headers.get("x-forwarded-for") ?? "",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
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
            { detail: data.detail ?? "Failed to refresh backend tokens" },
            { status: response.status || 500 },
        );
    }

    const nextResponse = NextResponse.json({ ok: true }, { status: 200 });
    const security = getCookieSecurity();

    nextResponse.cookies.set(ACCESS_TOKEN_COOKIE, data.access_token, security);
    nextResponse.cookies.set(REFRESH_TOKEN_COOKIE, data.refresh_token, security);
    nextResponse.cookies.set(CSRF_COOKIE, randomUUID(), {
        ...security,
        httpOnly: false,
    });

    return nextResponse;
}
