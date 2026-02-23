"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
  const [name, setName] = useState("");
  const [shortSummary, setShortSummary] = useState("");
  const [fullSummary, setFullSummary] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchDeck = useCallback(async () => {
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

      const mappedDeck: Deck = {
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
      };

      setDeck(mappedDeck);
      setName(mappedDeck.name);
      setShortSummary(mappedDeck.short_summary ?? "");
      setFullSummary(mappedDeck.full_summary ?? "");
    } catch (error) {
      console.error("Error fetching deck:", error);
    } finally {
      setLoading(false);
    }
  }, [deckId]);

  useEffect(() => {
    if (deckId) {
      void fetchDeck();
    }
  }, [deckId, fetchDeck]);

  const hasChanges = useMemo(() => {
    if (!deck) {
      return false;
    }

    return (
      name.trim() !== deck.name ||
      shortSummary !== (deck.short_summary ?? "") ||
      fullSummary !== (deck.full_summary ?? "")
    );
  }, [deck, fullSummary, name, shortSummary]);

  const handleSave = async () => {
    if (!deck || !name.trim()) {
      return;
    }

    setIsSaving(true);

    try {
      const response = await fetch(`/api/app/cards/deck/${deck.id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          short_summary: shortSummary,
          full_summary: fullSummary,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to update deck");
      }

      await fetchDeck();
    } catch (error) {
      console.error("Error updating deck:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deck) {
      return;
    }

    const confirmed = window.confirm(`Delete deck \"${deck.name}\"? This action cannot be undone.`);
    if (!confirmed) {
      return;
    }

    setIsDeleting(true);

    try {
      const response = await fetch(`/api/app/cards/deck/${deck.id}/`, {
        method: "DELETE",
      });

      if (!response.ok && response.status !== 204) {
        throw new Error("Failed to delete deck");
      }

      router.push("/dashboard");
    } catch (error) {
      console.error("Error deleting deck:", error);
      setIsDeleting(false);
    }
  };

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
                    <CardTitle className="text-3xl">Deck Details</CardTitle>
                    <CardDescription className="text-lg mt-2">
                      Total Cards: {totalCards} • Updated: {new Date(deck.date_updated).toLocaleString()}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button onClick={() => router.push(`/decks/generate?deckId=${deck.id}`)}>Regenerate</Button>
                    <Button variant="destructive" onClick={handleDelete} disabled={isDeleting || isSaving}>
                      {isDeleting ? "Deleting..." : "Delete Deck"}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="deckName">Name</Label>
                    <Textarea
                      id="deckName"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      rows={2}
                      disabled={isSaving || isDeleting}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="deckShortSummary">Short Description</Label>
                    <Textarea
                      id="deckShortSummary"
                      value={shortSummary}
                      onChange={(e) => setShortSummary(e.target.value)}
                      rows={3}
                      disabled={isSaving || isDeleting}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="deckLongSummary">Long Description</Label>
                    <Textarea
                      id="deckLongSummary"
                      value={fullSummary}
                      onChange={(e) => setFullSummary(e.target.value)}
                      rows={6}
                      disabled={isSaving || isDeleting}
                    />
                  </div>

                  <Button
                    onClick={handleSave}
                    disabled={isSaving || isDeleting || !name.trim() || !hasChanges}
                  >
                    {isSaving ? "Saving..." : "Save Deck Details"}
                  </Button>

                  <div className="space-y-2">
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
