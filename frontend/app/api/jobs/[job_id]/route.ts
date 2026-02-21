import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { jobStore } from "../../generate/route";

const BACKEND_MOCK = process.env.BACKEND_MOCK === "true";

export async function GET(
  req: NextRequest,
  { params }: { params: { job_id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (BACKEND_MOCK) {
    const jobId = params.job_id;
    const job = jobStore[jobId];

    if (!job) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    const elapsed = Date.now() - job.createdAt;
    const completionTime = 10000;

    if (elapsed < 2000) {
      job.status = "queued";
      job.progress = 0;
      job.message = "Deck generation queued";
    } else if (elapsed < completionTime) {
      job.status = "running";
      job.progress = Math.min(90, Math.floor((elapsed / completionTime) * 100));
      job.message = "Generating deck...";
    } else {
      job.status = "succeeded";
      job.progress = 100;
      job.message = "Deck generated successfully";
      job.deck_id = `deck_${jobId}`;
    }

    return NextResponse.json({
      status: job.status,
      progress: job.progress,
      message: job.message,
      deck_id: job.deck_id,
    });
  } else {
    return NextResponse.json(
      { error: "Backend mock disabled, use reverse proxy" },
      { status: 501 }
    );
  }
}
