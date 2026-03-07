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

import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import type { NextRequest } from "next/server";

const CSP_HEADER_NAME = "Content-Security-Policy";

function createNonce(): string {
    const uuid = crypto.randomUUID();
    if (typeof btoa === "function") {
        return btoa(uuid);
    }
    return Buffer.from(uuid, "utf-8").toString("base64");
}

function buildCspHeader(nonce: string): string {
    return [
        "default-src 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        `script-src 'self' 'nonce-${nonce}' https://static.cloudflareinsights.com`,
        `style-src 'self' 'nonce-${nonce}'`,
        "img-src 'self' data: blob: https:",
        "font-src 'self' data:",
        "connect-src 'self' https: wss: https://cloudflareinsights.com",
        "form-action 'self'",
        "upgrade-insecure-requests",
    ].join("; ");
}

function withNonceCsp(request: NextRequest): NextResponse {
    const nonce = createNonce();
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-nonce", nonce);

    const response = NextResponse.next({
        request: {
            headers: requestHeaders,
        },
    });
    response.headers.set(CSP_HEADER_NAME, buildCspHeader(nonce));
    return response;
}

export async function proxy(request: NextRequest) {
    const pathname = request.nextUrl.pathname;

    if (pathname.startsWith("/api/") || pathname.startsWith("/_next/") || pathname === "/favicon.ico") {
        return NextResponse.next();
    }

    const isAuthPage = pathname === "/login";
    const isProtectedRoute =
        pathname.startsWith("/dashboard") ||
        pathname.startsWith("/decks");

    if (isProtectedRoute || isAuthPage) {
        const token = await getToken({
            req: request,
            secret: process.env.NEXTAUTH_SECRET,
        });

        if (isProtectedRoute && !token) {
            return NextResponse.redirect(new URL("/login", request.url));
        }

        if (isAuthPage && token) {
            return NextResponse.redirect(new URL("/dashboard", request.url));
        }
    }

    return withNonceCsp(request);
}

export const config = {
    matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
