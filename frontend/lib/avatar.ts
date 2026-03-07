import type { Session } from "next-auth";

export const getAvatarUrlFromSession = (session: Session | null): string => {
    const sessionImage = session?.user?.image;
    if (sessionImage && sessionImage.trim().length > 0) {
        return sessionImage;
    }
    return "";
};
