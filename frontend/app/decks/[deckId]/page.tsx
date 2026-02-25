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
import { backendFetch, clearBackendTokens } from "@/lib/backend-auth";
import { getAvatarUrlFromSession } from "@/lib/avatar";

interface DeckCard {
  id: string;
  name: string;
  qty: number;
  text: string;
  llm_summary: string | null;
  types: string[];
  subtypes: string[];
  supertypes: string[];
  set_codes: string[];
  rarity: string;
  converted_mana_cost: number;
  mana_cost_colorless: number;
  mana_cost_white: number;
  mana_cost_blue: number;
  mana_cost_black: number;
  mana_cost_red: number;
  mana_cost_green: number;
  power: string | null;
  toughness: string | null;
  colors: string[];
  keywords: string[];
}

interface Deck {
  id: string;
  name: string;
  short_summary: string | null;
  full_summary: string | null;
  set_codes: string[];
  date_updated: string;
  creation_status: string | null;
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
  const [expandedCardIds, setExpandedCardIds] = useState<Set<string>>(new Set());

  const fetchDeck = useCallback(async () => {
    try {
      const response = await backendFetch(session, `/api/app/cards/deck/${deckId}/full/`);

      if (!response.ok) throw new Error("Failed to fetch deck");

      const data = (await response.json()) as {
        id: string;
        name: string;
        short_summary: string | null;
        full_summary: string | null;
        set_codes: string[];
        date_updated: string;
        creation_status: string | null;
        cards: [number, {
          id: string;
          name: string;
          text: string;
          llm_summary: string | null;
          types: string[];
          subtypes: string[];
          supertypes: string[];
          set_codes: string[];
          rarity: string;
          converted_mana_cost: number;
          mana_cost_colorless: number;
          mana_cost_white: number;
          mana_cost_blue: number;
          mana_cost_black: number;
          mana_cost_red: number;
          mana_cost_green: number;
          power: string | null;
          toughness: string | null;
          colors: string[];
          keywords: string[];
        }][];
      };

      const mappedDeck: Deck = {
        id: data.id,
        name: data.name,
        short_summary: data.short_summary,
        full_summary: data.full_summary,
        set_codes: data.set_codes,
        date_updated: data.date_updated,
        creation_status: data.creation_status,
        cards: data.cards.map(([qty, cardInfo]) => ({
          id: cardInfo.id,
          qty,
          name: cardInfo.name,
          text: cardInfo.text,
          llm_summary: cardInfo.llm_summary,
          types: cardInfo.types,
          subtypes: cardInfo.subtypes,
          supertypes: cardInfo.supertypes,
          set_codes: cardInfo.set_codes,
          rarity: cardInfo.rarity,
          converted_mana_cost: cardInfo.converted_mana_cost,
          mana_cost_colorless: cardInfo.mana_cost_colorless,
          mana_cost_white: cardInfo.mana_cost_white,
          mana_cost_blue: cardInfo.mana_cost_blue,
          mana_cost_black: cardInfo.mana_cost_black,
          mana_cost_red: cardInfo.mana_cost_red,
          mana_cost_green: cardInfo.mana_cost_green,
          power: cardInfo.power,
          toughness: cardInfo.toughness,
          colors: cardInfo.colors,
          keywords: cardInfo.keywords,
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
  }, [deckId, session]);

  useEffect(() => {
    if (deckId) {
      void fetchDeck();
    }
  }, [deckId, fetchDeck]);

  const updatePayload = useMemo(() => {
    if (!deck) {
      return null;
    }

    const trimmedName = name.trim();
    const trimmedShortSummary = shortSummary.trim();
    const trimmedFullSummary = fullSummary.trim();

    return {
      name: trimmedName.length === 0 || trimmedName === deck.name.trim() ? null : trimmedName,
      short_summary:
        trimmedShortSummary.length === 0 || trimmedShortSummary === (deck.short_summary ?? "").trim()
          ? null
          : trimmedShortSummary,
      full_summary:
        trimmedFullSummary.length === 0 || trimmedFullSummary === (deck.full_summary ?? "").trim()
          ? null
          : trimmedFullSummary,
    };
  }, [deck, fullSummary, name, shortSummary]);

  const hasChanges = useMemo(() => {
    if (!updatePayload) {
      return false;
    }

    return (
      updatePayload.name !== null ||
      updatePayload.short_summary !== null ||
      updatePayload.full_summary !== null
    );
  }, [updatePayload]);

  const handleSave = async () => {
    if (!deck || !updatePayload || isDeckBuilding) {
      return;
    }

    setIsSaving(true);

    try {
      const response = await backendFetch(session, `/api/app/cards/deck/${deck.id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatePayload),
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
    if (!deck || isDeckBuilding) {
      return;
    }

    const confirmed = window.confirm(`Delete deck \"${deck.name}\"? This action cannot be undone.`);
    if (!confirmed) {
      return;
    }

    setIsDeleting(true);

    try {
      const response = await backendFetch(session, `/api/app/cards/deck/${deck.id}/`, {
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

  const handleSignOut = async () => {
    clearBackendTokens();
    await signOut({ callbackUrl: "/login" });
  };

  const userInitials = session?.user?.name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase() || "U";
  const avatarUrl = getAvatarUrlFromSession(session);

  const totalCards = deck?.cards.reduce((sum, card) => sum + card.qty, 0) || 0;
  const isDeckBuilding = deck?.creation_status === "PENDING" || deck?.creation_status === "IN_PROGRESS";

  const formatManaCost = (card: DeckCard) => {
    const coloredMana = [
      ["W", card.mana_cost_white],
      ["U", card.mana_cost_blue],
      ["B", card.mana_cost_black],
      ["R", card.mana_cost_red],
      ["G", card.mana_cost_green],
    ] as const;

    const symbols = coloredMana
      .flatMap(([symbol, count]) => Array.from({ length: count }, () => symbol))
      .join("");

    if (card.mana_cost_colorless > 0) {
      return `${card.mana_cost_colorless}${symbols}`;
    }

    return symbols || "0";
  };

  const toggleCardExpanded = (cardId: string) => {
    setExpandedCardIds((current) => {
      const next = new Set(current);
      if (next.has(cardId)) {
        next.delete(cardId);
      } else {
        next.add(cardId);
      }
      return next;
    });
  };

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
                    <AvatarImage src={avatarUrl} />
                    <AvatarFallback>{userInitials}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{session?.user?.name}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleSignOut}>
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
                      Total Cards: {totalCards} • Updated: {new Date(deck.date_updated).toISOString()}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={() => router.push(`/decks/generate?deckId=${deck.id}`)}
                      disabled={isDeckBuilding || isDeleting || isSaving}
                    >
                      Regenerate
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleDelete}
                      disabled={isDeckBuilding || isDeleting || isSaving}
                    >
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
                    disabled={isDeckBuilding || isSaving || isDeleting || !hasChanges}
                  >
                    {isSaving ? "Saving..." : "Save Deck Details"}
                  </Button>

                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">
                      Sets: {deck.set_codes.length > 0 ? deck.set_codes.join(", ") : "None"}
                    </p>
                  </div>

                  <div className="space-y-1">
                    {deck.cards.map((card, index) => {
                      const isExpanded = expandedCardIds.has(card.id);
                      const typeLine = [...card.supertypes, ...card.types, ...card.subtypes].join(" ");

                      return (
                        <div
                          key={`${card.id}-${index}`}
                          className="rounded border"
                        >
                          <button
                            type="button"
                            className="w-full flex items-center justify-between py-2 px-3 text-left hover:bg-secondary/50 transition-colors"
                            onClick={() => toggleCardExpanded(card.id)}
                          >
                            <span className="font-medium">{card.name}</span>
                            <span className="text-sm text-muted-foreground">×{card.qty}</span>
                          </button>

                          {isExpanded ? (
                            <div className="border-t px-3 py-3 space-y-2 text-sm">
                              <p className="text-muted-foreground">
                                {typeLine || "No type information"}
                              </p>
                              <p>
                                <span className="font-medium">Mana Cost:</span> {formatManaCost(card)}
                              </p>
                              <p>
                                <span className="font-medium">Power/Toughness:</span>{" "}
                                {card.power && card.toughness ? `${card.power}/${card.toughness}` : "N/A"}
                              </p>
                              <p>
                                <span className="font-medium">Rarity:</span> {card.rarity}
                              </p>
                              <p>
                                <span className="font-medium">Keywords:</span> {card.keywords.length > 0 ? card.keywords.join(", ") : "None"}
                              </p>
                              <p>
                                <span className="font-medium">Set Codes:</span> {card.set_codes.length > 0 ? card.set_codes.join(", ") : "None"}
                              </p>
                              <p>{card.text || "No rules text available."}</p>
                              {card.llm_summary ? <p className="text-muted-foreground">{card.llm_summary}</p> : null}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
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
