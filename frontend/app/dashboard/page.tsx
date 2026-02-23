"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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

    const fetchDecks = useCallback(async () => {
        const response = await fetch("/api/app/cards/deck/");
        if (!response.ok) {
            throw new Error("Failed to fetch deck summaries");
        }

        const data = (await response.json()) as DeckSummary[];
        setDecks(data);
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

                    {isLoading ? (
                        <Card>
                            <CardContent className="flex items-center justify-center py-12">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </CardContent>
                        </Card>
                    ) : null}

                    {!isLoading && decks.length === 0 ? (
                        <Card>
                            <CardHeader>
                                <CardTitle>No decks yet</CardTitle>
                                <CardDescription>Create your first deck to get started.</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <Button onClick={() => router.push("/decks/generate")}>Go to Deck Generation</Button>
                            </CardContent>
                        </Card>
                    ) : null}

                    {!isLoading
                        ? decks.map((deck) => (
                            <Card
                                key={deck.id}
                                className="cursor-pointer transition-colors hover:bg-secondary/20"
                                onClick={() => router.push(`/decks/${deck.id}`)}
                            >
                                <CardHeader>
                                    <CardTitle className="text-xl">{deck.name}</CardTitle>
                                    <CardDescription>
                                        Status: {deck.generation_status ?? "UNKNOWN"} • Updated: {new Date(deck.date_updated).toLocaleString()}
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
