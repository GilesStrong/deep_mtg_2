"use client";

import { useEffect } from "react";
import { useSession, SessionProvider } from "next-auth/react";

import { clearBackendTokens, ensureBackendTokens } from "@/lib/backend-auth";

function BackendUserSync() {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status !== "authenticated") {
      clearBackendTokens();
      return;
    }

    const sync = async () => {
      try {
        await ensureBackendTokens(session);
      } catch (error) {
        console.error("Error syncing backend auth tokens:", error);
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
