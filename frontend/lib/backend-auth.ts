import type { Session } from "next-auth";

const BACKEND_AUTH_EXCHANGE_PATH = "/backend-auth/exchange";
const BACKEND_AUTH_REFRESH_PATH = "/backend-auth/refresh";
const BACKEND_AUTH_CLEAR_PATH = "/backend-auth/clear";

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
    const runRequest = async (): Promise<Response> =>
        fetch(input, {
            ...init,
            credentials: "same-origin",
        });

    await ensureBackendTokens(session);

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
