import type { Session } from "next-auth";

type GoogleIdTokenClaims = {
    picture?: string;
};

const decodeGoogleIdTokenClaims = (googleIdToken: string): GoogleIdTokenClaims | null => {
    const parts = googleIdToken.split(".");
    if (parts.length < 2) {
        return null;
    }

    try {
        const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
        const paddedPayload = payload.padEnd(Math.ceil(payload.length / 4) * 4, "=");
        const decoded = atob(paddedPayload);
        return JSON.parse(decoded) as GoogleIdTokenClaims;
    } catch {
        return null;
    }
};

export const getAvatarUrlFromSession = (session: Session | null): string => {
    const sessionImage = session?.user?.image;
    if (sessionImage && sessionImage.trim().length > 0) {
        return sessionImage;
    }

    const googleIdToken = session?.user?.googleAuthToken;
    if (!googleIdToken) {
        return "";
    }

    const claims = decodeGoogleIdTokenClaims(googleIdToken);
    if (claims?.picture && claims.picture.trim().length > 0) {
        return claims.picture;
    }

    return "";
};
