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

const REGENERATE_NAV_MARKER_KEY = "deep-mtg.regenerate-nav";
const ROLE_DISPLAY_ORDER = [
  "WinCon",
  "Primary Engine",
  "Interaction",
  "Ramp & Card Advantage",
  "Support",
  "Flex & filler",
  "Land",
] as const;
const IMPORTANCE_DISPLAY_ORDER = ["Critical", "High Synergy", "Functional", "Generic"] as const;
const roleOrderIndex = new Map<string, number>(
  ROLE_DISPLAY_ORDER.map((role, index) => [role, index])
);
const importanceOrderIndex = new Map<string, number>(
  IMPORTANCE_DISPLAY_ORDER.map((importance, index) => [importance, index])
);

interface CardInfo {
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
  tags: string[];
}

interface DeckCard extends CardInfo {
  qty: number;
  role: string;
  importance: string;
  possible_replacements: CardInfo[];
}

interface Deck {
  id: string;
  name: string;
  short_summary: string | null;
  full_summary: string | null;
  set_codes: string[];
  tags: string[];
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
  const [isArenaImportExpanded, setIsArenaImportExpanded] = useState(false);
  const [arenaImportCopied, setArenaImportCopied] = useState(false);
  const [expandedCardIds, setExpandedCardIds] = useState<Set<string>>(new Set());
  const [replacementModalCard, setReplacementModalCard] = useState<DeckCard | null>(null);

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
        tags?: string[];
        date_updated: string;
        creation_status: string | null;
        cards: {
          quantity: number;
          role?: string | null;
          importance?: string | null;
          card_info: {
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
            tags?: string[];
          };
          possible_replacements?: {
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
            tags?: string[];
          }[];
        }[];
      };

      const mapCardInfo = (cardInfo: CardInfo): CardInfo => ({
        id: cardInfo.id,
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
        tags: cardInfo.tags ?? [],
      });

      const mappedDeck: Deck = {
        id: data.id,
        name: data.name,
        short_summary: data.short_summary,
        full_summary: data.full_summary,
        set_codes: data.set_codes,
        tags: data.tags ?? [],
        date_updated: data.date_updated,
        creation_status: data.creation_status,
        cards: data.cards.map((card) => ({
          ...mapCardInfo(card.card_info),
          qty: card.quantity,
          role: card.role ?? "Uncategorized",
          importance: card.importance ?? "Not specified",
          possible_replacements: (card.possible_replacements ?? []).map(mapCardInfo),
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

  useEffect(() => {
    if (!replacementModalCard) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setReplacementModalCard(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [replacementModalCard]);

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

  const arenaImportText = useMemo(() => {
    if (!deck) {
      return "";
    }

    const lines = [
      "About",
      `Name ${deck.name}`,
      "",
      "Deck",
      ...deck.cards.map((card) => `${card.qty} ${card.name}`),
    ];

    return lines.join("\n");
  }, [deck]);

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

  const cardsByRole = useMemo(() => {
    if (!deck) {
      return [] as Array<{ role: string; cards: DeckCard[] }>;
    }

    const groupedCards = new Map<string, DeckCard[]>();
    for (const card of deck.cards) {
      const role = card.role.trim().length > 0 ? card.role : "Uncategorized";
      const roleCards = groupedCards.get(role);
      if (roleCards) {
        roleCards.push(card);
      } else {
        groupedCards.set(role, [card]);
      }
    }

    return Array.from(groupedCards.entries())
      .map(([role, cards]) => ({
        role,
        cards: [...cards].sort((leftCard, rightCard) => {
          const leftImportance = importanceOrderIndex.get(leftCard.importance);
          const rightImportance = importanceOrderIndex.get(rightCard.importance);

          if (leftImportance === undefined && rightImportance === undefined) {
            return leftCard.name.localeCompare(rightCard.name);
          }
          if (leftImportance === undefined) {
            return 1;
          }
          if (rightImportance === undefined) {
            return -1;
          }
          if (leftImportance !== rightImportance) {
            return leftImportance - rightImportance;
          }

          return leftCard.name.localeCompare(rightCard.name);
        }),
      }))
      .sort((leftGroup, rightGroup) => {
        const leftRoleOrder = roleOrderIndex.get(leftGroup.role);
        const rightRoleOrder = roleOrderIndex.get(rightGroup.role);

        if (leftRoleOrder === undefined && rightRoleOrder === undefined) {
          return leftGroup.role.localeCompare(rightGroup.role);
        }
        if (leftRoleOrder === undefined) {
          return 1;
        }
        if (rightRoleOrder === undefined) {
          return -1;
        }

        return leftRoleOrder - rightRoleOrder;
      });
  }, [deck]);

  const formatManaCost = (card: CardInfo) => {
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

  const handleRegenerate = () => {
    sessionStorage.setItem(
      REGENERATE_NAV_MARKER_KEY,
      JSON.stringify({ deckId: deck?.id ?? null, createdAt: Date.now() })
    );
    router.push(`/decks/generate?deckId=${deck?.id ?? deckId}`);
  };

  const handleCopyArenaImport = async () => {
    if (!arenaImportText) {
      return;
    }

    try {
      await navigator.clipboard.writeText(arenaImportText);
      setArenaImportCopied(true);
      window.setTimeout(() => setArenaImportCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy arena import text:", error);
    }
  };

  const getTypeLine = (card: CardInfo): string => [...card.supertypes, ...card.types, ...card.subtypes].join(" ");

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
                <DropdownMenuItem onClick={() => router.push("/dashboard/account")}>Account</DropdownMenuItem>
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
                      variant="outline"
                      onClick={() => router.push(`/cards/search?deckId=${deck?.id ?? deckId}`)}
                      disabled={isDeckBuilding || isDeleting || isSaving}
                    >
                      Search Cards
                    </Button>
                    <Button
                      onClick={handleRegenerate}
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
                      Tags: {deck.tags.length > 0 ? deck.tags.join(", ") : "None"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Sets: {deck.set_codes.length > 0 ? deck.set_codes.join(", ") : "None"}
                    </p>
                  </div>

                  <div className="rounded border">
                    <div className="w-full flex items-center justify-between py-2 px-3 hover:bg-secondary/50 transition-colors">
                      <button
                        type="button"
                        className="flex-1 text-left"
                        onClick={() => setIsArenaImportExpanded((current) => !current)}
                      >
                        <span className="font-medium">MTG Arena Import Format</span>
                        <span className="ml-3 text-sm text-muted-foreground">
                          {isArenaImportExpanded ? "Hide" : "Show"}
                        </span>
                      </button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleCopyArenaImport();
                        }}
                      >
                        {arenaImportCopied ? "Copied" : "Copy"}
                      </Button>
                    </div>

                    {isArenaImportExpanded ? (
                      <div className="border-t px-3 py-3">
                        <Textarea
                          value={arenaImportText}
                          readOnly
                          rows={Math.max(8, Math.min(24, deck.cards.length + 6))}
                          className="font-mono text-sm"
                        />
                      </div>
                    ) : null}
                  </div>

                  <div className="space-y-4">
                    {cardsByRole.map((roleGroup) => (
                      <div key={roleGroup.role} className="space-y-2">
                        <h3 className="text-base font-semibold">{roleGroup.role}</h3>
                        <div className="space-y-1">
                          {roleGroup.cards.map((card, index) => {
                            const isExpanded = expandedCardIds.has(card.id);
                            const typeLine = getTypeLine(card);

                            return (
                              <div
                                key={`${roleGroup.role}-${card.id}-${index}`}
                                className="rounded border"
                              >
                                <div className="w-full flex items-center justify-between py-2 px-3 hover:bg-secondary/50 transition-colors gap-3">
                                  <button
                                    type="button"
                                    className="flex-1 text-left"
                                    onClick={() => toggleCardExpanded(card.id)}
                                  >
                                    <span className="font-medium">{card.name}</span>
                                    <p className="text-sm text-muted-foreground">
                                      Importance: {card.importance}
                                    </p>
                                  </button>
                                  <div className="flex items-center gap-2">
                                    {card.possible_replacements.length > 0 ? (
                                      <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={(event) => {
                                          event.stopPropagation();
                                          setReplacementModalCard(card);
                                        }}
                                      >
                                        View replacements ({card.possible_replacements.length})
                                      </Button>
                                    ) : null}
                                    <span className="text-sm text-muted-foreground">×{card.qty}</span>
                                  </div>
                                </div>

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
                                    <div>
                                      <span className="font-medium">Tags:</span>
                                      {card.tags.length > 0 ? (
                                        <ul className="list-disc list-inside mt-1">
                                          {card.tags.map((tag) => (
                                            <li key={tag}>{tag}</li>
                                          ))}
                                        </ul>
                                      ) : (
                                        <p>None</p>
                                      )}
                                    </div>
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

      {replacementModalCard ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80"
          onClick={() => setReplacementModalCard(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={`Replacement cards for ${replacementModalCard.name}`}
            className="w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-lg border bg-card text-card-foreground shadow-sm"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div>
                <h3 className="text-lg font-semibold">Replacement Cards</h3>
                <p className="text-sm text-muted-foreground">For {replacementModalCard.name}</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => setReplacementModalCard(null)}>
                Close
              </Button>
            </div>
            <div className="p-4 space-y-3">
              {replacementModalCard.possible_replacements.map((replacementCard) => {
                const typeLine = getTypeLine(replacementCard);
                return (
                  <div key={replacementCard.id} className="rounded border p-3 space-y-2 text-sm">
                    <p className="font-medium">{replacementCard.name}</p>
                    <p className="text-muted-foreground">{typeLine || "No type information"}</p>
                    <p>
                      <span className="font-medium">Mana Cost:</span> {formatManaCost(replacementCard)}
                    </p>
                    <p>
                      <span className="font-medium">Rarity:</span> {replacementCard.rarity}
                    </p>
                    <p>{replacementCard.text || "No rules text available."}</p>
                    {replacementCard.llm_summary ? (
                      <p className="text-muted-foreground">{replacementCard.llm_summary}</p>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
