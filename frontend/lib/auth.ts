import { AuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

type GoogleIdTokenClaims = {
  picture?: string;
  name?: string;
  email?: string;
};

const decodeJwtPayload = (jwtToken: string): GoogleIdTokenClaims | null => {
  const parts = jwtToken.split(".");
  if (parts.length < 2) {
    return null;
  }

  try {
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const paddedPayload = payload.padEnd(Math.ceil(payload.length / 4) * 4, "=");
    const decoded = Buffer.from(paddedPayload, "base64").toString("utf-8");
    return JSON.parse(decoded) as GoogleIdTokenClaims;
  } catch {
    return null;
  }
};

export const authOptions: AuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async redirect({ url, baseUrl }) {
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      else if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
    async jwt({ token, account, profile }) {
      if (account?.id_token) {
        token.googleAuthToken = account.id_token;

        const claims = decodeJwtPayload(account.id_token);
        if (!token.picture && typeof claims?.picture === "string") {
          token.picture = claims.picture;
        }
        if (!token.name && typeof claims?.name === "string") {
          token.name = claims.name;
        }
        if (!token.email && typeof claims?.email === "string") {
          token.email = claims.email;
        }
      }

      if (profile && "picture" in profile && typeof profile.picture === "string") {
        token.picture = profile.picture;
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        if (typeof token.googleAuthToken === "string") {
          session.user.googleAuthToken = token.googleAuthToken;
        }

        if (typeof token.picture === "string") {
          session.user.image = token.picture;
        }

        if (typeof token.name === "string") {
          session.user.name = token.name;
        }

        if (typeof token.email === "string") {
          session.user.email = token.email;
        }
      }

      return session;
    },
  },
};
