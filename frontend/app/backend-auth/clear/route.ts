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

const ACCESS_TOKEN_COOKIE = "backend_access_token";
const REFRESH_TOKEN_COOKIE = "backend_refresh_token";
const CSRF_COOKIE = "backend_csrf_token";

const getCookieSecurity = () => ({
    httpOnly: true,
    sameSite: "lax" as const,
    secure: false,
    path: "/",
});

export async function POST(): Promise<NextResponse> {
    const nextResponse = NextResponse.json({ ok: true }, { status: 200 });
    const security = getCookieSecurity();

    nextResponse.cookies.set(ACCESS_TOKEN_COOKIE, "", { ...security, maxAge: 0 });
    nextResponse.cookies.set(REFRESH_TOKEN_COOKIE, "", { ...security, maxAge: 0 });
    nextResponse.cookies.set(CSRF_COOKIE, "", { ...security, httpOnly: false, maxAge: 0 });

    return nextResponse;
}
