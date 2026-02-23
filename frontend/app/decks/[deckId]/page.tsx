"use client";

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ArrowLeft, Loader2 } from "lucide-react";

interface DeckCard {
  name: string;
  qty: number;
}

interface Deck {
  id: string;
  name: string;
  short_summary: string | null;
  full_summary: string | null;
  set_codes: string[];
  date_updated: string;
  cards: DeckCard[];
}

export default function DeckPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const params = useParams();
  const deckId = params.deckId as string;
  const [deck, setDeck] = useState<Deck | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDeck = async () => {
      try {
        const response = await fetch(`/api/app/cards/deck/${deckId}/full/`);
        if (!response.ok) throw new Error("Failed to fetch deck");

        const data = (await response.json()) as {
          id: string;
          name: string;
          short_summary: string | null;
          full_summary: string | null;
          set_codes: string[];
          date_updated: string;
          cards: [number, { name: string }][];
        };

        setDeck({
          id: data.id,
          name: data.name,
          short_summary: data.short_summary,
          full_summary: data.full_summary,
          set_codes: data.set_codes,
          date_updated: data.date_updated,
          cards: data.cards.map(([qty, cardInfo]) => ({
            qty,
            name: cardInfo.name,
          })),
        });
      } catch (error) {
        console.error("Error fetching deck:", error);
      } finally {
        setLoading(false);
      }
    };

    if (deckId) {
      fetchDeck();
    }
  }, [deckId]);

  const userInitials = session?.user?.name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase() || "U";

  const totalCards = deck?.cards.reduce((sum, card) => sum + card.qty, 0) || 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Deep MTG</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {session?.user?.email}
            </span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                  <Avatar>
                    <AvatarImage src={session?.user?.image || ""} />
                    <AvatarFallback>{userInitials}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{session?.user?.name}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => signOut({ callbackUrl: "/login" })}>
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <Button variant="ghost" onClick={() => router.push("/dashboard")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>

          {loading ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </CardContent>
            </Card>
          ) : deck ? (
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-3xl">{deck.name}</CardTitle>
                    <CardDescription className="text-lg mt-2">
                      Total Cards: {totalCards} • Updated: {new Date(deck.date_updated).toLocaleString()}
                    </CardDescription>
                  </div>
                  <Button onClick={() => router.push(`/decks/generate?deckId=${deck.id}`)}>Regenerate</Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">{deck.short_summary ?? "No short summary available."}</p>
                    <p className="text-sm">{deck.full_summary ?? "No full summary available."}</p>
                    <p className="text-xs text-muted-foreground">
                      Sets: {deck.set_codes.length > 0 ? deck.set_codes.join(", ") : "None"}
                    </p>
                  </div>

                  <div className="space-y-1">
                    {deck.cards.map((card, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between py-2 px-3 rounded hover:bg-secondary/50 transition-colors"
                      >
                        <span className="font-medium">{card.name}</span>
                        <span className="text-sm text-muted-foreground">×{card.qty}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">Deck not found</p>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
