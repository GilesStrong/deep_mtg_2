import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

const BACKEND_MOCK = process.env.BACKEND_MOCK === "true";

interface JobStore {
  [jobId: string]: {
    status: "queued" | "running" | "succeeded" | "failed";
    progress: number;
    message: string;
    deck_id?: string;
    createdAt: number;
  };
}

const jobStore: JobStore = {};

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (BACKEND_MOCK) {
    const body = await req.json();
    const jobId = `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    jobStore[jobId] = {
      status: "queued",
      progress: 0,
      message: "Deck generation queued",
      createdAt: Date.now(),
    };

    return NextResponse.json({ job_id: jobId });
  } else {
    return NextResponse.json(
      { error: "Backend mock disabled, use reverse proxy" },
      { status: 501 }
    );
  }
}

export { jobStore };
