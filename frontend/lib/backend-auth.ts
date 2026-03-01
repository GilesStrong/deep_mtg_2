import type { Session } from "next-auth";

const BACKEND_AUTH_EXCHANGE_PATH = "/backend-auth/exchange";
const BACKEND_AUTH_REFRESH_PATH = "/backend-auth/refresh";
const BACKEND_AUTH_CLEAR_PATH = "/backend-auth/clear";
const BACKEND_CSRF_COOKIE_NAME = "backend_csrf_token";

const parseBackendErrorMessage = async (response: Response, fallbackMessage: string): Promise<string> => {
    try {
        const data = (await response.json()) as {
            detail?: string;
            message?: string;
            error?: string;
        };
        return data.detail ?? data.message ?? data.error ?? fallbackMessage;
    } catch {
        return fallbackMessage;
    }
};

const exchangeGoogleToken = async (googleIdToken: string): Promise<void> => {
    const response = await fetch(BACKEND_AUTH_EXCHANGE_PATH, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ google_id_token: googleIdToken }),
        credentials: "same-origin",
    });

    if (!response.ok) {
        throw new Error(await parseBackendErrorMessage(response, "Failed to exchange Google token"));
    }
};

const refreshBackendTokens = async (): Promise<void> => {
    const response = await fetch(BACKEND_AUTH_REFRESH_PATH, {
        method: "POST",
        credentials: "same-origin",
    });

    if (!response.ok) {
        throw new Error(await parseBackendErrorMessage(response, "Failed to refresh backend tokens"));
    }
};

const getCookieValue = (name: string): string | null => {
    if (typeof document === "undefined") {
        return null;
    }

    const encodedName = encodeURIComponent(name);
    const target = `${encodedName}=`;
    const parts = document.cookie.split(";");
    for (const part of parts) {
        const trimmed = part.trim();
        if (trimmed.startsWith(target)) {
            return decodeURIComponent(trimmed.slice(target.length));
        }
    }
    return null;
};

const isUnsafeMethod = (method: string): boolean => {
    return ["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase());
};

export const ensureBackendTokens = async (session: Session | null): Promise<void> => {
    const googleIdToken = session?.user?.googleAuthToken;

    if (!googleIdToken) {
        throw new Error("Missing Google ID token in session");
    }

    await exchangeGoogleToken(googleIdToken);
};

export const clearBackendTokens = (): void => {
    void fetch(BACKEND_AUTH_CLEAR_PATH, {
        method: "POST",
        credentials: "same-origin",
    });
};

export const backendFetch = async (
    session: Session | null,
    input: RequestInfo | URL,
    init?: RequestInit
): Promise<Response> => {
    const runRequest = async (): Promise<Response> => {
        const method = (init?.method ?? "GET").toUpperCase();
        const headers = new Headers(init?.headers);
        if (isUnsafeMethod(method)) {
            const csrfToken = getCookieValue(BACKEND_CSRF_COOKIE_NAME);
            if (csrfToken) {
                headers.set("X-Backend-CSRF", csrfToken);
            }
        }

        return fetch(input, {
            ...init,
            method,
            headers,
            credentials: "same-origin",
        });
    };

    let response = await runRequest();
    if (response.status !== 401) {
        return response;
    }

    try {
        await refreshBackendTokens();
        response = await runRequest();
        if (response.status !== 401) {
            return response;
        }
    } catch {
        clearBackendTokens();
    }

    const googleIdToken = session?.user?.googleAuthToken;
    if (!googleIdToken) {
        return response;
    }

    await exchangeGoogleToken(googleIdToken);
    return runRequest();
};
