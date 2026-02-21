import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

const BACKEND_MOCK = process.env.BACKEND_MOCK === "true";

const mockDecks: { [key: string]: any } = {};

export async function GET(
  req: NextRequest,
  { params }: { params: { deck_id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  if (BACKEND_MOCK) {
    const deckId = params.deck_id;
    
    if (!mockDecks[deckId]) {
      mockDecks[deckId] = {
        id: deckId,
        name: "AI Generated Commander Deck",
        format: "commander",
        cards: [
          { name: "Sol Ring", qty: 1 },
          { name: "Command Tower", qty: 1 },
          { name: "Arcane Signet", qty: 1 },
          { name: "Lightning Greaves", qty: 1 },
          { name: "Swiftfoot Boots", qty: 1 },
          { name: "Cyclonic Rift", qty: 1 },
          { name: "Counterspell", qty: 1 },
          { name: "Rhystic Study", qty: 1 },
          { name: "Mystical Tutor", qty: 1 },
          { name: "Ponder", qty: 1 },
          { name: "Brainstorm", qty: 1 },
          { name: "Island", qty: 35 },
          { name: "Mountain", qty: 35 },
          { name: "Steam Vents", qty: 1 },
          { name: "Sulfur Falls", qty: 1 },
        ],
      };
    }

    return NextResponse.json(mockDecks[deckId]);
  } else {
    return NextResponse.json(
      { error: "Backend mock disabled, use reverse proxy" },
      { status: 501 }
    );
  }
}
