"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { backendFetch, clearBackendTokens } from "@/lib/backend-auth";
import { getAvatarUrlFromSession } from "@/lib/avatar";

const QUERY_MIN_LENGTH = 20;
const QUERY_MAX_LENGTH = 200;

const COLOR_FILTERS = [
    { code: "W", label: "White" },
    { code: "U", label: "Blue" },
    { code: "B", label: "Black" },
    { code: "R", label: "Red" },
    { code: "G", label: "Green" },
] as const;

type SearchCard = {
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
};

type SearchResult = {
    card_info: SearchCard;
    relevance_score: number;
};

type HierarchicalTags = Record<string, Record<string, string>>;

type TagEndpointPayload = {
    tags?: string[] | HierarchicalTags;
} & Record<string, unknown>;

const normalizeHierarchicalTags = (input: unknown): HierarchicalTags => {
    if (!input || typeof input !== "object" || Array.isArray(input)) {
        return {};
    }

    const normalized: HierarchicalTags = {};

    for (const [primaryTag, rawSubtags] of Object.entries(input as Record<string, unknown>)) {
        if (typeof primaryTag !== "string" || primaryTag.trim().length === 0) {
            continue;
        }

        if (!rawSubtags || typeof rawSubtags !== "object" || Array.isArray(rawSubtags)) {
            continue;
        }

        const subtags: Record<string, string> = {};
        for (const [subtag, description] of Object.entries(rawSubtags as Record<string, unknown>)) {
            if (typeof subtag !== "string" || subtag.trim().length === 0) {
                continue;
            }

            subtags[subtag] = typeof description === "string" ? description : "";
        }

        normalized[primaryTag] = subtags;
    }

    return normalized;
};

const parseTagPayload = (rawPayload: unknown): HierarchicalTags => {
    if (!rawPayload || typeof rawPayload !== "object") {
        return {};
    }

    const payload = rawPayload as TagEndpointPayload;

    if (Array.isArray(payload.tags)) {
        const flatTags = [...new Set(payload.tags.filter((tag) => tag.trim().length > 0))].sort((a, b) =>
            a.localeCompare(b)
        );

        return flatTags.reduce<HierarchicalTags>((acc, tag) => {
            acc[tag] = {};
            return acc;
        }, {});
    }

    if (payload.tags && typeof payload.tags === "object" && !Array.isArray(payload.tags)) {
        return normalizeHierarchicalTags(payload.tags);
    }

    return normalizeHierarchicalTags(payload);
};

const parseApiError = async (response: Response, fallbackMessage: string): Promise<string> => {
    const responseText = await response.text();
    if (!responseText) {
        return fallbackMessage;
    }

    try {
        const data = JSON.parse(responseText) as {
            detail?: string | Array<{ msg?: string }>;
            message?: string;
            error?: string;
        };

        if (typeof data.detail === "string") {
            return data.detail;
        }

        if (Array.isArray(data.detail)) {
            const firstDetail = data.detail.find((item) => item.msg)?.msg;
            if (firstDetail) {
                return firstDetail;
            }
        }

        return data.message ?? data.error ?? fallbackMessage;
    } catch {
        return responseText.trim() || fallbackMessage;
    }
};

export default function CardSearchPage() {
    const { data: session } = useSession();
    const router = useRouter();
    const searchParams = useSearchParams();
    const sourceDeckId = searchParams.get("deckId");

    const [query, setQuery] = useState("");
    const [availableSetCodes, setAvailableSetCodes] = useState<string[]>([]);
    const [selectedSetCodes, setSelectedSetCodes] = useState<string[]>([]);
    const [availableTagsByPrimary, setAvailableTagsByPrimary] = useState<HierarchicalTags>({});
    const [selectedTags, setSelectedTags] = useState<string[]>([]);
    const [selectedColors, setSelectedColors] = useState<string[]>([]);
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [isLoadingFilters, setIsLoadingFilters] = useState(true);
    const [isSearching, setIsSearching] = useState(false);
    const [searchError, setSearchError] = useState<string | null>(null);
    const [expandedCardIds, setExpandedCardIds] = useState<Set<string>>(new Set());
    const [hasAppliedDeckContext, setHasAppliedDeckContext] = useState(false);

    const userInitials =
        session?.user?.name
            ?.split(" ")
            .map((part) => part[0])
            .join("")
            .toUpperCase() || "U";
    const avatarUrl = getAvatarUrlFromSession(session);

    const availablePrimaryTags = useMemo(
        () => Object.keys(availableTagsByPrimary).sort((a, b) => a.localeCompare(b)),
        [availableTagsByPrimary]
    );

    const availableSubtags = useMemo(() => {
        const subtags = new Set<string>();

        for (const primaryTag of availablePrimaryTags) {
            for (const subtag of Object.keys(availableTagsByPrimary[primaryTag] ?? {})) {
                subtags.add(subtag);
            }
        }

        return subtags;
    }, [availablePrimaryTags, availableTagsByPrimary]);

    useEffect(() => {
        const loadFilters = async () => {
            try {
                const [setCodesResponse, tagsResponse] = await Promise.all([
                    backendFetch(session, "/api/app/cards/card/set_codes/"),
                    backendFetch(session, "/api/app/cards/card/tags/"),
                ]);

                if (!setCodesResponse.ok || !tagsResponse.ok) {
                    throw new Error("Failed to fetch card search filters");
                }

                const setCodesData = (await setCodesResponse.json()) as { set_codes: string[] };
                const tagsData = (await tagsResponse.json()) as unknown;

                setAvailableSetCodes([...setCodesData.set_codes].sort((a, b) => a.localeCompare(b)));
                setAvailableTagsByPrimary(parseTagPayload(tagsData));
            } catch (error) {
                console.error("Error loading card search filters:", error);
                setAvailableSetCodes([]);
                setAvailableTagsByPrimary({});
            } finally {
                setIsLoadingFilters(false);
            }
        };

        if (!session) {
            return;
        }

        void loadFilters();
    }, [session]);

    useEffect(() => {
        if (!session || !sourceDeckId || hasAppliedDeckContext) {
            return;
        }

        const loadDeckContext = async () => {
            try {
                const response = await backendFetch(session, `/api/app/cards/deck/${sourceDeckId}/full/`);
                if (!response.ok) {
                    throw new Error("Failed to load source deck context");
                }

                const data = (await response.json()) as {
                    short_summary: string | null;
                    set_codes: string[];
                    cards: Array<
                        | [number, { colors: string[]; tags?: string[]; set_codes: string[] }]
                        | {
                              quantity: number;
                              card_info: { colors: string[]; tags?: string[]; set_codes: string[] };
                          }
                    >;
                };

                const summary = data.short_summary?.trim() ?? "";
                if (summary.length > 0) {
                    setQuery(summary);
                }

                const deckSetCodes = new Set<string>(data.set_codes);
                const deckColors = new Set<string>();
                const deckTags = new Set<string>();

                for (const rawCardEntry of data.cards) {
                    const card = Array.isArray(rawCardEntry) ? rawCardEntry[1] : rawCardEntry.card_info;

                    for (const color of card.colors) {
                        if (COLOR_FILTERS.some((filterColor) => filterColor.code === color)) {
                            deckColors.add(color);
                        }
                    }

                    for (const setCode of card.set_codes) {
                        deckSetCodes.add(setCode);
                    }

                    for (const tag of card.tags ?? []) {
                        if (tag.trim().length > 0) {
                            deckTags.add(tag);
                        }
                    }
                }

                setSelectedSetCodes(Array.from(deckSetCodes));
                setSelectedColors(Array.from(deckColors));
                setSelectedTags(Array.from(deckTags));
            } catch (error) {
                console.error("Error loading source deck context:", error);
            } finally {
                setHasAppliedDeckContext(true);
            }
        };

        void loadDeckContext();
    }, [hasAppliedDeckContext, session, sourceDeckId]);

    useEffect(() => {
        if (availableSetCodes.length === 0) {
            return;
        }

        setSelectedSetCodes((current) => current.filter((setCode) => availableSetCodes.includes(setCode)));
    }, [availableSetCodes]);

    useEffect(() => {
        if (availableSubtags.size === 0) {
            return;
        }

        setSelectedTags((current) => current.filter((tag) => availableSubtags.has(tag)));
    }, [availableSubtags]);

    const toggleSetCode = (setCode: string) => {
        setSelectedSetCodes((current) =>
            current.includes(setCode) ? current.filter((value) => value !== setCode) : [...current, setCode]
        );
    };

    const toggleTag = (tag: string) => {
        setSelectedTags((current) => (current.includes(tag) ? current.filter((value) => value !== tag) : [...current, tag]));
    };

    const toggleColor = (color: string) => {
        setSelectedColors((current) =>
            current.includes(color) ? current.filter((value) => value !== color) : [...current, color]
        );
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

    const formatManaCost = (card: SearchCard): string => {
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

    const queryLength = query.trim().length;
    const isQueryLengthInvalid = queryLength < QUERY_MIN_LENGTH || queryLength > QUERY_MAX_LENGTH;

    const typeLineForCard = (card: SearchCard): string => {
        return [...card.supertypes, ...card.types, ...card.subtypes].join(" ");
    };

    const selectedSubtags = useMemo(
        () => selectedTags.filter((tag) => availableSubtags.has(tag)),
        [availableSubtags, selectedTags]
    );

    const handleSearch = async () => {
        const trimmedQuery = query.trim();
        if (trimmedQuery.length < QUERY_MIN_LENGTH || trimmedQuery.length > QUERY_MAX_LENGTH) {
            return;
        }

        setIsSearching(true);
        setSearchError(null);
        setExpandedCardIds(new Set());

        try {
            const response = await backendFetch(session, "/api/app/search/search/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: trimmedQuery,
                    set_codes: selectedSetCodes,
                    colors: selectedColors,
                    tags: selectedSubtags,
                }),
            });

            if (!response.ok) {
                throw new Error(await parseApiError(response, "Failed to search cards"));
            }

            const data = (await response.json()) as { cards: SearchResult[] };
            const sortedResults = [...data.cards].sort((a, b) => b.relevance_score - a.relevance_score);
            setSearchResults(sortedResults);
        } catch (error) {
            console.error("Error searching cards:", error);
            setSearchResults([]);
            setSearchError(error instanceof Error ? error.message : "Failed to search cards");
        } finally {
            setIsSearching(false);
        }
    };

    const handleSignOut = async () => {
        try {
            await clearBackendTokens();
        } finally {
            await signOut({ callbackUrl: "/login" });
        }
    };

    const activeFilterCount = useMemo(
        () => selectedSetCodes.length + selectedSubtags.length + selectedColors.length,
        [selectedColors.length, selectedSetCodes.length, selectedSubtags.length]
    );

    return (
        <div className="flex-1 bg-gradient-to-br from-slate-50 to-slate-100">
            <header className="border-b bg-white/80 backdrop-blur-sm">
                <div className="container mx-auto flex items-center justify-between px-4 py-4">
                    <h1 className="text-2xl font-bold">Deep MTG</h1>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-muted-foreground">{session?.user?.email}</span>
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
                                <DropdownMenuItem onClick={handleSignOut}>Sign out</DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-4 py-8">
                <div className="mx-auto max-w-4xl space-y-6">
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" onClick={() => router.push("/dashboard")}>
                            <ArrowLeft className="mr-2 h-4 w-4" />
                            Back to Dashboard
                        </Button>
                        {sourceDeckId ? (
                            <Button variant="outline" onClick={() => router.push(`/decks/${sourceDeckId}`)}>
                                Back to Deck
                            </Button>
                        ) : null}
                    </div>

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-xl">Card Search</CardTitle>
                            <CardDescription>
                                Enter a detailed query and optional filters to find relevant cards.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-2">
                                <Label htmlFor="card-search-query">Query</Label>
                                <Textarea
                                    id="card-search-query"
                                    rows={3}
                                    value={query}
                                    onChange={(event) => setQuery(event.target.value)}
                                    placeholder="Describe the cards you want to find..."
                                />
                                <p className="text-xs text-muted-foreground">
                                    Query length: {queryLength} / {QUERY_MAX_LENGTH} (min {QUERY_MIN_LENGTH})
                                </p>
                            </div>

                            <div className="space-y-2">
                                <Label>Colors</Label>
                                <div className="flex flex-wrap gap-2">
                                    {COLOR_FILTERS.map(({ code, label }) => {
                                        const isSelected = selectedColors.includes(code);
                                        return (
                                            <Button
                                                key={code}
                                                type="button"
                                                size="sm"
                                                variant={isSelected ? "default" : "outline"}
                                                onClick={() => toggleColor(code)}
                                            >
                                                {label}
                                            </Button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label>Set Codes</Label>
                                {isLoadingFilters ? (
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Loading set codes and tags...
                                    </div>
                                ) : availableSetCodes.length === 0 ? (
                                    <p className="text-sm text-muted-foreground">No set codes available.</p>
                                ) : (
                                    <div className="flex flex-wrap gap-2">
                                        {availableSetCodes.map((setCode) => {
                                            const isSelected = selectedSetCodes.includes(setCode);
                                            return (
                                                <Button
                                                    key={setCode}
                                                    type="button"
                                                    size="sm"
                                                    variant={isSelected ? "default" : "outline"}
                                                    onClick={() => toggleSetCode(setCode)}
                                                >
                                                    {setCode}
                                                </Button>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label>Tags</Label>
                                {isLoadingFilters ? null : availablePrimaryTags.length === 0 ? (
                                    <p className="text-sm text-muted-foreground">No tags available.</p>
                                ) : (
                                    <div className="space-y-3">
                                        {availablePrimaryTags.map((primaryTag) => {
                                            const subtags = availableTagsByPrimary[primaryTag] ?? {};
                                            const sortedSubtags = Object.keys(subtags).sort((a, b) => a.localeCompare(b));

                                            return (
                                                <div key={primaryTag} className="space-y-2">
                                                    <div className="flex items-center gap-2">
                                                        <p className="text-sm font-semibold">{primaryTag}</p>
                                                    </div>

                                                    {sortedSubtags.length > 0 ? (
                                                        <div className="flex flex-row flex-wrap items-center gap-2">
                                                            {sortedSubtags.map((subtag) => {
                                                                const isSubtagSelected = selectedTags.includes(subtag);
                                                                const description = subtags[subtag] ?? "";

                                                                return (
                                                                    <Button
                                                                        key={`${primaryTag}-${subtag}`}
                                                                        type="button"
                                                                        size="sm"
                                                                        variant={isSubtagSelected ? "default" : "outline"}
                                                                        onClick={() => toggleTag(subtag)}
                                                                        title={description || subtag}
                                                                        aria-pressed={isSubtagSelected}
                                                                        className="h-8"
                                                                    >
                                                                        {subtag}
                                                                    </Button>
                                                                );
                                                            })}
                                                        </div>
                                                    ) : null}
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            <p className="text-xs text-muted-foreground">
                                {activeFilterCount === 0
                                    ? "No filters active."
                                    : `${activeFilterCount} filter${activeFilterCount === 1 ? "" : "s"} selected.`}
                            </p>

                            <Button onClick={handleSearch} disabled={isSearching || isQueryLengthInvalid}>
                                {isSearching ? "Searching..." : "Search Cards"}
                            </Button>

                            {isQueryLengthInvalid ? (
                                <p className="text-sm text-muted-foreground">
                                    Query must be between {QUERY_MIN_LENGTH} and {QUERY_MAX_LENGTH} characters.
                                </p>
                            ) : null}

                            {searchError ? <p className="text-sm text-destructive">{searchError}</p> : null}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-xl">Results</CardTitle>
                            <CardDescription>
                                {searchResults.length === 0
                                    ? "No cards found yet. Run a search to see results."
                                    : `${searchResults.length} card${searchResults.length === 1 ? "" : "s"} found.`}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {searchResults.length === 0 ? (
                                <p className="text-sm text-muted-foreground">Results will appear here.</p>
                            ) : (
                                <div className="space-y-1">
                                    {searchResults.map((result) => {
                                        const card = result.card_info;
                                        const isExpanded = expandedCardIds.has(card.id);
                                        const typeLine = typeLineForCard(card);

                                        return (
                                            <div key={card.id} className="rounded border">
                                                <button
                                                    type="button"
                                                    className="w-full px-3 py-2 text-left transition-colors hover:bg-secondary/50"
                                                    onClick={() => toggleCardExpanded(card.id)}
                                                >
                                                    <div className="flex items-center justify-between gap-4">
                                                        <span className="font-medium">{card.name}</span>
                                                        <span className="text-xs text-muted-foreground">{formatManaCost(card)}</span>
                                                    </div>
                                                    <p className="mt-1 text-xs text-muted-foreground">
                                                        {typeLine || "No type information"}
                                                        {card.rarity ? ` • ${card.rarity}` : ""}
                                                    </p>
                                                </button>

                                                {isExpanded ? (
                                                    <div className="space-y-2 border-t px-3 py-3 text-sm">
                                                        <p className="text-muted-foreground">{typeLine || "No type information"}</p>
                                                        <p>
                                                            <span className="font-medium">Mana Cost:</span> {formatManaCost(card)}
                                                        </p>
                                                        <p>
                                                            <span className="font-medium">Power/Toughness:</span>{" "}
                                                            {card.power && card.toughness ? `${card.power}/${card.toughness}` : "N/A"}
                                                        </p>
                                                        <p>
                                                            <span className="font-medium">Rarity:</span> {card.rarity || "N/A"}
                                                        </p>
                                                        <p>
                                                            <span className="font-medium">Colors:</span>{" "}
                                                            {card.colors.length > 0 ? card.colors.join(", ") : "None"}
                                                        </p>
                                                        <p>
                                                            <span className="font-medium">Keywords:</span>{" "}
                                                            {card.keywords.length > 0 ? card.keywords.join(", ") : "None"}
                                                        </p>
                                                        <div>
                                                            <span className="font-medium">Tags:</span>
                                                            {card.tags.length > 0 ? (
                                                                <ul className="mt-1 list-inside list-disc">
                                                                    {card.tags.map((tag) => (
                                                                        <li key={`${card.id}-${tag}`}>{tag}</li>
                                                                    ))}
                                                                </ul>
                                                            ) : (
                                                                <p>None</p>
                                                            )}
                                                        </div>
                                                        <p>
                                                            <span className="font-medium">Set Codes:</span>{" "}
                                                            {card.set_codes.length > 0 ? card.set_codes.join(", ") : "None"}
                                                        </p>
                                                        <p>{card.text || "No rules text available."}</p>
                                                        {card.llm_summary ? <p className="text-muted-foreground">{card.llm_summary}</p> : null}
                                                    </div>
                                                ) : null}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </main>
        </div>
    );
}
