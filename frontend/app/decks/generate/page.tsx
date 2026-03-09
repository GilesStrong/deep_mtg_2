/*
Copyright 2026 Giles Strong

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

"use client";

export const dynamic = "force-dynamic";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ArrowLeft, Loader2 } from "lucide-react";
import { backendFetch, clearBackendTokens } from "@/lib/backend-auth";
import { getAvatarUrlFromSession } from "@/lib/avatar";

const REGENERATE_NAV_MARKER_KEY = "deep-mtg.regenerate-nav";
const REGENERATE_NAV_MARKER_MAX_AGE_MS = 60_000;
const PROMPT_MIN_LENGTH = 20;
const PROMPT_MAX_LENGTH = 3000;
const DAILY_THEME_REFRESH_INTERVAL_MS = 10 * 60 * 1000;
const TOAST_DURATION_MS = 4000;

function GenerateDeckPageContent() {
    const { data: session } = useSession();
    const router = useRouter();
    const searchParams = useSearchParams();
    const rawDeckId = searchParams.get("deckId");
    const queryTheme = searchParams.get("theme");

    const [prompt, setPrompt] = useState("");
    const [regenerationDeckId, setRegenerationDeckId] = useState<string | null>(null);
    const [regenerationDeckName, setRegenerationDeckName] = useState<string | null>(null);
    const [isLoadingRegenerationDeckName, setIsLoadingRegenerationDeckName] = useState(false);
    const [availableSetCodes, setAvailableSetCodes] = useState<string[]>([]);
    const [selectedSetCodes, setSelectedSetCodes] = useState<string[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingSetCodes, setIsLoadingSetCodes] = useState(true);
    const [remainingQuota, setRemainingQuota] = useState<number | null>(null);
    const [isLoadingQuota, setIsLoadingQuota] = useState(true);
    const [generationError, setGenerationError] = useState<string | null>(null);
    const [dailyTheme, setDailyTheme] = useState<string | null>(null);
    const [toastMessage, setToastMessage] = useState<string | null>(null);

    const parseApiError = async (response: Response, fallbackMessage: string): Promise<string> => {
        const responseText = await response.text();
        if (!responseText) {
            return fallbackMessage;
        }

        try {
            const data = JSON.parse(responseText) as {
                detail?:
                | string
                | Array<{
                    msg?: string;
                }>;
                message?: string;
                error?: string;
            };

            if (typeof data.detail === "string") {
                return data.detail;
            }

            if (Array.isArray(data.detail)) {
                const firstMessage = data.detail.find((item) => item?.msg)?.msg;
                if (firstMessage) {
                    return firstMessage;
                }
            }

            return data.message ?? data.error ?? fallbackMessage;
        } catch {
            return responseText.trim() || fallbackMessage;
        }
    };

    const showToast = useCallback((message: string): void => {
        setToastMessage(message);
        window.setTimeout(() => {
            setToastMessage((current) => (current === message ? null : current));
        }, TOAST_DURATION_MS);
    }, []);

    const userInitials =
        session?.user?.name
            ?.split(" ")
            .map((n) => n[0])
            .join("")
            .toUpperCase() || "U";
    const avatarUrl = getAvatarUrlFromSession(session);

    useEffect(() => {
        if (!rawDeckId) {
            sessionStorage.removeItem(REGENERATE_NAV_MARKER_KEY);
            setRegenerationDeckId(null);
            return;
        }

        if (regenerationDeckId === rawDeckId) {
            return;
        }

        const markerRaw = sessionStorage.getItem(REGENERATE_NAV_MARKER_KEY);

        if (!markerRaw) {
            setRegenerationDeckId(null);
            router.replace("/decks/generate");
            return;
        }

        try {
            const marker = JSON.parse(markerRaw) as { deckId?: string | null; createdAt?: number };
            const markerDeckId = marker.deckId ?? null;
            const markerCreatedAt = marker.createdAt ?? 0;
            const isFresh = Date.now() - markerCreatedAt <= REGENERATE_NAV_MARKER_MAX_AGE_MS;

            if (!isFresh || !markerDeckId || markerDeckId !== rawDeckId) {
                setRegenerationDeckId(null);
                sessionStorage.removeItem(REGENERATE_NAV_MARKER_KEY);
                router.replace("/decks/generate");
                return;
            }

            setRegenerationDeckId(rawDeckId);
        } catch {
            setRegenerationDeckId(null);
            sessionStorage.removeItem(REGENERATE_NAV_MARKER_KEY);
            router.replace("/decks/generate");
        }
    }, [rawDeckId, regenerationDeckId, router]);

    useEffect(() => {
        if (!queryTheme || rawDeckId) {
            return;
        }

        setPrompt(queryTheme);
        setDailyTheme(queryTheme);
    }, [queryTheme, rawDeckId]);

    useEffect(() => {
        if (!session || rawDeckId || queryTheme) {
            setDailyTheme(null);
            return;
        }

        const loadDailyTheme = async () => {
            const response = await backendFetch(session, "/api/app/cards/deck/daily_theme/");
            if (!response.ok) {
                setDailyTheme(null);
                return;
            }

            try {
                const data = (await response.json()) as string;
                setDailyTheme(data);
            } catch {
                setDailyTheme(null);
            }
        };

        void loadDailyTheme();

        const interval = setInterval(() => {
            void loadDailyTheme();
        }, DAILY_THEME_REFRESH_INTERVAL_MS);

        return () => clearInterval(interval);
    }, [queryTheme, rawDeckId, session]);

    useEffect(() => {
        if (!regenerationDeckId || !session) {
            setRegenerationDeckName(null);
            setIsLoadingRegenerationDeckName(false);
            return;
        }

        const loadRegenerationDeckName = async () => {
            setIsLoadingRegenerationDeckName(true);
            try {
                const response = await backendFetch(session, `/api/app/cards/deck/${regenerationDeckId}/`);
                if (!response.ok) {
                    throw new Error("Failed to fetch regeneration deck");
                }

                const data = (await response.json()) as { name?: string };
                setRegenerationDeckName(data.name ?? null);
            } catch (error) {
                console.error("Error loading regeneration deck name:", error);
                setRegenerationDeckName(null);
            } finally {
                setIsLoadingRegenerationDeckName(false);
            }
        };

        void loadRegenerationDeckName();
    }, [regenerationDeckId, session]);

    useEffect(() => {
        const loadSetCodes = async () => {
            try {
                const response = await backendFetch(session, "/api/app/cards/card/set_codes/");
                if (!response.ok) {
                    throw new Error("Failed to fetch set codes");
                }

                const data = (await response.json()) as { set_codes: string[] };
                const sortedCodes = [...data.set_codes].sort((a, b) => a.localeCompare(b));
                setAvailableSetCodes(sortedCodes);
                setSelectedSetCodes(sortedCodes);
            } catch (error) {
                console.error("Error loading set codes:", error);
                setAvailableSetCodes([]);
                setSelectedSetCodes([]);
            } finally {
                setIsLoadingSetCodes(false);
            }
        };

        if (!session) {
            return;
        }

        void loadSetCodes();
    }, [session]);

    const loadRemainingQuota = useCallback(async () => {
        if (!session) {
            return;
        }

        try {
            const response = await backendFetch(session, "/api/app/ai/deck/remaining_quota/");
            if (!response.ok) {
                throw new Error("Failed to fetch remaining quota");
            }

            const data = (await response.json()) as { remaining: number };
            setRemainingQuota(Math.max(0, data.remaining));
        } catch (error) {
            console.error("Error loading remaining quota:", error);
            setRemainingQuota(null);
        } finally {
            setIsLoadingQuota(false);
        }
    }, [session]);

    useEffect(() => {
        if (!session) {
            return;
        }

        setIsLoadingQuota(true);
        void loadRemainingQuota();

        const interval = setInterval(() => {
            void loadRemainingQuota();
        }, 60000);

        return () => clearInterval(interval);
    }, [loadRemainingQuota, session]);

    const toggleSetCode = (code: string) => {
        if (isGenerating) {
            return;
        }

        setSelectedSetCodes((current) => {
            if (current.includes(code)) {
                return current.filter((value) => value !== code);
            }

            return [...current, code];
        });
    };

    const handleGenerateDeck = async () => {
        if (
            !prompt.trim() ||
            prompt.length < PROMPT_MIN_LENGTH ||
            prompt.length > PROMPT_MAX_LENGTH ||
            selectedSetCodes.length === 0 ||
            remainingQuota === 0
        ) {
            return;
        }

        setGenerationError(null);
        setIsGenerating(true);

        try {
            const payload: { prompt: string; set_codes: string[]; deck_id?: string } = {
                prompt,
                set_codes: selectedSetCodes,
            };

            if (regenerationDeckId) {
                payload.deck_id = regenerationDeckId;
            }

            const response = await backendFetch(session, "/api/app/ai/deck/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorMessage = await parseApiError(response, "Failed to start deck generation");
                if (response.status === 409) {
                    showToast(errorMessage);
                }
                throw new Error(errorMessage);
            }

            const data = (await response.json()) as { task_id: string; deck_id: string };
            if (!data.task_id || !data.deck_id) {
                throw new Error("Build task was created but response was missing task or deck identifiers.");
            }

            router.push(`/decks/${data.deck_id}?taskId=${data.task_id}`);
            setRemainingQuota((current) => {
                if (current === null) {
                    return current;
                }

                return Math.max(0, current - 1);
            });
        } catch (error) {
            console.error("Error generating deck:", error);
            setIsGenerating(false);
            setGenerationError(error instanceof Error ? error.message : "Failed to start deck generation");
            void loadRemainingQuota();
        }
    };

    const isQuotaExceeded = remainingQuota === 0;
    const promptLength = prompt.length;
    const isPromptLengthInvalid = promptLength < PROMPT_MIN_LENGTH || promptLength > PROMPT_MAX_LENGTH;
    const isSubmitDisabled =
        !prompt.trim() || isPromptLengthInvalid || isGenerating || isLoadingSetCodes || selectedSetCodes.length === 0 || isQuotaExceeded;

    const handleSignOut = async () => {
        clearBackendTokens();
        await signOut({ callbackUrl: "/login" });
    };

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
                <div className="mx-auto max-w-2xl space-y-6">
                    <Button variant="ghost" onClick={() => router.push("/dashboard")}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Decks
                    </Button>

                    <Card>
                        <CardHeader>
                            <CardTitle>{regenerationDeckId ? "Regenerate Deck" : "Generate Deck"}</CardTitle>
                            <CardDescription>
                                {regenerationDeckId
                                    ? "Submit a new prompt to rebuild this existing deck."
                                    : "Describe the deck you want and start a generation task."}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {!rawDeckId && dailyTheme ? (
                                <div className="space-y-2">
                                    <p className="text-sm text-muted-foreground">
                                        <strong>Today&apos;s theme:</strong> {dailyTheme}
                                    </p>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        onClick={() => setPrompt(dailyTheme)}
                                        disabled={isGenerating}
                                    >
                                        Generate this deck
                                    </Button>
                                </div>
                            ) : null}

                            {regenerationDeckId ? (
                                <p className="text-sm text-muted-foreground">
                                    Target deck:{" "}
                                    {isLoadingRegenerationDeckName
                                        ? "Loading..."
                                        : regenerationDeckName ?? "Unknown deck"}
                                </p>
                            ) : null}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between gap-2">
                                    <Label htmlFor="prompt">Prompt</Label>
                                    <p className="text-xs text-muted-foreground" aria-live="polite">
                                        {promptLength}/{PROMPT_MAX_LENGTH}
                                    </p>
                                </div>
                                <Textarea
                                    id="prompt"
                                    placeholder="A blue-red spellslinger deck with strong instant-speed interaction..."
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    rows={5}
                                    disabled={isGenerating}
                                />
                                {isPromptLengthInvalid ? (
                                    <p className="text-xs text-muted-foreground">
                                        Prompt must be between {PROMPT_MIN_LENGTH} and {PROMPT_MAX_LENGTH} characters.
                                    </p>
                                ) : null}
                            </div>
                            <div className="space-y-2">
                                <Label>Set Codes</Label>
                                {isLoadingSetCodes ? (
                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Loading set codes...
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <div className="flex flex-wrap gap-2">
                                            {availableSetCodes.map((code) => {
                                                const isSelected = selectedSetCodes.includes(code);

                                                return (
                                                    <Button
                                                        key={code}
                                                        type="button"
                                                        variant={isSelected ? "default" : "outline"}
                                                        size="sm"
                                                        disabled={isGenerating}
                                                        onClick={() => toggleSetCode(code)}
                                                    >
                                                        {code}
                                                    </Button>
                                                );
                                            })}
                                        </div>
                                        <p className="text-xs text-muted-foreground">Generation requires at least one selected set code.</p>
                                    </div>
                                )}
                            </div>
                            <Button
                                onClick={handleGenerateDeck}
                                disabled={isSubmitDisabled}
                                className="w-full"
                                size="lg"
                            >
                                {isGenerating ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    "Submit Generation Task"
                                )}
                            </Button>
                            <p className="text-sm text-muted-foreground">
                                {isLoadingQuota
                                    ? "Checking remaining builds..."
                                    : remainingQuota === null
                                        ? "Unable to load remaining builds right now."
                                        : `Remaining builds today: ${remainingQuota}`}
                            </p>
                            {isQuotaExceeded ? (
                                <p className="text-sm text-muted-foreground">
                                    You have no remaining builds for today. Generation will be available again after midnight.
                                </p>
                            ) : null}
                            {generationError ? <p className="text-sm">{generationError}</p> : null}
                        </CardContent>
                    </Card>
                </div>
            </main>

            {toastMessage ? (
                <div className="fixed right-4 top-4 z-50 max-w-sm rounded border bg-card px-4 py-3 text-sm shadow-sm" role="status" aria-live="polite">
                    {toastMessage}
                </div>
            ) : null}
        </div>
    );
}

export default function GenerateDeckPage() {
    return (
        <Suspense fallback={<div className="flex-1 bg-gradient-to-br from-slate-50 to-slate-100" />}>
            <GenerateDeckPageContent />
        </Suspense>
    );
}
