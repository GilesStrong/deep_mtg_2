import type { Session } from "next-auth";

const BACKEND_ACCESS_TOKEN_STORAGE_KEY = "deep_mtg_backend_access_token";
const BACKEND_REFRESH_TOKEN_STORAGE_KEY = "deep_mtg_backend_refresh_token";
const BACKEND_USER_EMAIL_STORAGE_KEY = "deep_mtg_backend_user_email";

type BackendTokens = {
    accessToken: string;
    refreshToken: string;
};

const isBrowser = () => typeof window !== "undefined";

const getStoredEmail = (): string | null => {
    if (!isBrowser()) {
        return null;
    }

    return window.localStorage.getItem(BACKEND_USER_EMAIL_STORAGE_KEY);
};

const getStoredTokens = (): BackendTokens | null => {
    if (!isBrowser()) {
        return null;
    }

    const accessToken = window.localStorage.getItem(BACKEND_ACCESS_TOKEN_STORAGE_KEY);
    const refreshToken = window.localStorage.getItem(BACKEND_REFRESH_TOKEN_STORAGE_KEY);

    if (!accessToken || !refreshToken) {
        return null;
    }

    return { accessToken, refreshToken };
};

const storeTokens = (tokens: BackendTokens, email: string | null): void => {
    if (!isBrowser()) {
        return;
    }

    window.localStorage.setItem(BACKEND_ACCESS_TOKEN_STORAGE_KEY, tokens.accessToken);
    window.localStorage.setItem(BACKEND_REFRESH_TOKEN_STORAGE_KEY, tokens.refreshToken);
    if (email) {
        window.localStorage.setItem(BACKEND_USER_EMAIL_STORAGE_KEY, email);
    }
};

export const clearBackendTokens = (): void => {
    if (!isBrowser()) {
        return;
    }

    window.localStorage.removeItem(BACKEND_ACCESS_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(BACKEND_REFRESH_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(BACKEND_USER_EMAIL_STORAGE_KEY);
};

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

const exchangeGoogleToken = async (googleIdToken: string): Promise<BackendTokens> => {
    const response = await fetch("/api/app/token/exchange", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ google_id_token: googleIdToken }),
    });

    if (!response.ok) {
        throw new Error(await parseBackendErrorMessage(response, "Failed to exchange Google token"));
    }

    const data = (await response.json()) as { access_token: string; refresh_token: string };
    return { accessToken: data.access_token, refreshToken: data.refresh_token };
};

const refreshBackendTokens = async (refreshToken: string): Promise<BackendTokens> => {
    const response = await fetch("/api/app/token/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
        throw new Error(await parseBackendErrorMessage(response, "Failed to refresh backend tokens"));
    }

    const data = (await response.json()) as { access_token: string; refresh_token: string };
    return { accessToken: data.access_token, refreshToken: data.refresh_token };
};

export const ensureBackendTokens = async (session: Session | null): Promise<BackendTokens> => {
    const email = session?.user?.email ?? null;
    const googleIdToken = session?.user?.googleAuthToken;

    if (!googleIdToken) {
        throw new Error("Missing Google ID token in session");
    }

    const storedEmail = getStoredEmail();
    if (email && storedEmail && storedEmail !== email) {
        clearBackendTokens();
    }

    const storedTokens = getStoredTokens();
    if (storedTokens) {
        return storedTokens;
    }

    const tokens = await exchangeGoogleToken(googleIdToken);
    storeTokens(tokens, email);
    return tokens;
};

const withAuthorizationHeader = (headers: HeadersInit | undefined, accessToken: string): Headers => {
    const mergedHeaders = new Headers(headers);
    mergedHeaders.set("Authorization", `Bearer ${accessToken}`);
    return mergedHeaders;
};

export const backendFetch = async (
    session: Session | null,
    input: RequestInfo | URL,
    init?: RequestInit
): Promise<Response> => {
    const email = session?.user?.email ?? null;

    const runRequest = async (accessToken: string): Promise<Response> =>
        fetch(input, {
            ...init,
            headers: withAuthorizationHeader(init?.headers, accessToken),
        });

    const tokens = await ensureBackendTokens(session);
    let response = await runRequest(tokens.accessToken);
    if (response.status !== 401) {
        return response;
    }

    try {
        const refreshedTokens = await refreshBackendTokens(tokens.refreshToken);
        storeTokens(refreshedTokens, email);
        response = await runRequest(refreshedTokens.accessToken);
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

    const exchangedTokens = await exchangeGoogleToken(googleIdToken);
    storeTokens(exchangedTokens, email);
    return runRequest(exchangedTokens.accessToken);
};
