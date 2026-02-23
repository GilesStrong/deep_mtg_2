"use client";

import { useEffect } from "react";
import { useSession, SessionProvider } from "next-auth/react";

import { clearCachedBackendUserId, syncBackendUserId } from "@/lib/backend-user";

function BackendUserSync() {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status !== "authenticated") {
      clearCachedBackendUserId();
      return;
    }

    const sync = async () => {
      try {
        await syncBackendUserId(session);
      } catch (error) {
        console.error("Error syncing backend user ID:", error);
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
