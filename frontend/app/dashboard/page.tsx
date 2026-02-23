"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Label } from "@/components/ui/label";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Loader2 } from "lucide-react";

type DeckSummary = {
    id: string;
    name: string;
    short_summary: string | null;
    set_codes: string[];
    date_updated: string;
    generation_status: string | null;
    generation_task_id: string | null;
};

const POLLABLE_STATUSES = new Set(["PENDING", "IN_PROGRESS"]);

export default function DashboardPage() {
    const { data: session } = useSession();
    const router = useRouter();
    const [decks, setDecks] = useState<DeckSummary[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [availableSetCodes, setAvailableSetCodes] = useState<string[]>([]);
    const [selectedSetCodes, setSelectedSetCodes] = useState<string[]>([]);
    const [isLoadingSetCodes, setIsLoadingSetCodes] = useState(true);

    const fetchDecks = useCallback(async () => {
        const response = await fetch("/api/app/cards/deck/");
        if (!response.ok) {
            throw new Error("Failed to fetch deck summaries");
        }

        const data = (await response.json()) as DeckSummary[];
        setDecks(data);
    }, []);

    useEffect(() => {
        const loadSetCodes = async () => {
            try {
                const response = await fetch("/api/app/cards/card/set_codes/");
                if (!response.ok) {
                    throw new Error("Failed to fetch set codes");
                }

                const data = (await response.json()) as { set_codes: string[] };
                const sortedCodes = [...data.set_codes].sort((a, b) => a.localeCompare(b));
                setAvailableSetCodes(sortedCodes);
            } catch (error) {
                console.error("Error loading set codes:", error);
                setAvailableSetCodes([]);
            } finally {
                setIsLoadingSetCodes(false);
            }
        };

        void loadSetCodes();
    }, []);

    useEffect(() => {
        const load = async () => {
            try {
                await fetchDecks();
            } catch (error) {
                console.error("Error loading decks:", error);
            } finally {
                setIsLoading(false);
            }
        };

        void load();
    }, [fetchDecks]);

    const activeDecks = useMemo(
        () =>
            decks.filter(
                (deck) =>
                    deck.generation_status &&
                    POLLABLE_STATUSES.has(deck.generation_status) &&
                    Boolean(deck.generation_task_id)
            ),
        [decks]
    );

    useEffect(() => {
        if (activeDecks.length === 0) {
            return;
        }

        const interval = setInterval(async () => {
            try {
                await Promise.all(
                    activeDecks.map(async (deck) => {
                        if (!deck.generation_task_id) {
                            return;
                        }

                        const statusResponse = await fetch(`/api/app/ai/deck/build_status/${deck.generation_task_id}/`);
                        if (!statusResponse.ok) {
                            return;
                        }

                        const statusData = (await statusResponse.json()) as { status: string; deck_id: string };
                        setDecks((current) =>
                            current.map((item) =>
                                item.id === statusData.deck_id ? { ...item, generation_status: statusData.status } : item
                            )
                        );
                    })
                );

                await fetchDecks();
            } catch (error) {
                console.error("Error polling deck statuses:", error);
            }
        }, 2500);

        return () => clearInterval(interval);
    }, [activeDecks, fetchDecks]);

    const userInitials =
        session?.user?.name
            ?.split(" ")
            .map((n) => n[0])
            .join("")
            .toUpperCase() || "U";

    const toggleSetCode = (code: string) => {
        setSelectedSetCodes((current) =>
            current.includes(code) ? current.filter((value) => value !== code) : [...current, code]
        );
    };

    const filteredDecks = useMemo(() => {
        if (selectedSetCodes.length === 0) {
            return decks;
        }

        return decks.filter((deck) => deck.set_codes.some((code) => selectedSetCodes.includes(code)));
    }, [decks, selectedSetCodes]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
            <header className="border-b bg-white/80 backdrop-blur-sm">
                <div className="container mx-auto flex items-center justify-between px-4 py-4">
                    <h1 className="text-2xl font-bold">Deep MTG</h1>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-muted-foreground">{session?.user?.email}</span>
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
                                <DropdownMenuItem onClick={() => signOut({ callbackUrl: "/login" })}>Sign out</DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-4 py-8">
                <div className="mx-auto max-w-4xl space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-semibold">Decks</h2>
                        <Button onClick={() => router.push("/decks/generate")}>Generate Deck</Button>
                    </div>

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Filter by Set Code</CardTitle>
                            <CardDescription>
                                Select one or more set codes to show only decks that include cards from those sets.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {isLoadingSetCodes ? (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Loading set codes...
                                </div>
                            ) : availableSetCodes.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No set codes available.</p>
                            ) : (
                                <div className="space-y-2">
                                    <Label>Set Codes</Label>
                                    <div className="flex flex-wrap gap-2">
                                        {availableSetCodes.map((code) => {
                                            const isSelected = selectedSetCodes.includes(code);

                                            return (
                                                <Button
                                                    key={code}
                                                    type="button"
                                                    size="sm"
                                                    variant={isSelected ? "default" : "outline"}
                                                    onClick={() => toggleSetCode(code)}
                                                >
                                                    {code}
                                                </Button>
                                            );
                                        })}
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        {selectedSetCodes.length === 0
                                            ? "No filter active. Showing all decks."
                                            : `Filter active: ${selectedSetCodes.length} set code${selectedSetCodes.length === 1 ? "" : "s"} selected.`}
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {isLoading ? (
                        <Card>
                            <CardContent className="flex items-center justify-center py-12">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </CardContent>
                        </Card>
                    ) : null}

                    {!isLoading && filteredDecks.length === 0 ? (
                        <Card>
                            <CardHeader>
                                <CardTitle>No decks found</CardTitle>
                                <CardDescription>
                                    {decks.length === 0
                                        ? "Create your first deck to get started."
                                        : "Try adjusting your set code filter."}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {decks.length === 0 ? (
                                    <Button onClick={() => router.push("/decks/generate")}>Go to Deck Generation</Button>
                                ) : (
                                    <Button onClick={() => setSelectedSetCodes([])} variant="outline">
                                        Clear Filter
                                    </Button>
                                )}
                            </CardContent>
                        </Card>
                    ) : null}

                    {!isLoading
                        ? filteredDecks.map((deck) => (
                            <Card
                                key={deck.id}
                                className="cursor-pointer transition-colors hover:bg-secondary/20"
                                onClick={() => router.push(`/decks/${deck.id}`)}
                            >
                                <CardHeader>
                                    <CardTitle className="text-xl">{deck.name}</CardTitle>
                                    <CardDescription>
                                        Status: {deck.generation_status ?? "UNKNOWN"} • Updated: {new Date(deck.date_updated).toISOString()}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-2">
                                    <p className="text-sm text-muted-foreground">
                                        {deck.short_summary ?? "No summary available yet."}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        Sets: {deck.set_codes.length > 0 ? deck.set_codes.join(", ") : "None"}
                                    </p>
                                </CardContent>
                            </Card>
                        ))
                        : null}
                </div>
            </main>
        </div>
    );
}
