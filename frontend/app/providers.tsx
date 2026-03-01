"use client";

import { useEffect } from "react";
import { signOut, useSession, SessionProvider } from "next-auth/react";

import { clearBackendTokens, ensureBackendTokens } from "@/lib/backend-auth";

function BackendUserSync() {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status !== "authenticated") {
      void clearBackendTokens();
      return;
    }

    const sync = async () => {
      try {
        await ensureBackendTokens(session);
      } catch (error) {
        console.error("Error syncing backend auth tokens:", error);
        try {
          await clearBackendTokens();
        } catch (clearError) {
          console.error("Error clearing backend auth tokens:", clearError);
        }

        const message =
          error instanceof Error && error.message
            ? error.message
            : "Unable to complete sign in. Please try again.";
        const callbackUrl = `/login?error=${encodeURIComponent(message)}`;
        await signOut({ callbackUrl });
      }
    };

    void sync();
  }, [session, status]);

  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <BackendUserSync />
      {children}
    </SessionProvider>
  );
}
