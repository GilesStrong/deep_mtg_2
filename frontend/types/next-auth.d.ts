import { DefaultSession } from "next-auth";

declare module "next-auth" {
    interface Session {
        user: DefaultSession["user"] & {
            googleAuthToken?: string;
        };
    }
}

declare module "next-auth/jwt" {
    interface JWT {
        googleAuthToken?: string;
    }
}
