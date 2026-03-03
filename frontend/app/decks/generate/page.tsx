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
const BUILD_STATUS_TIMEOUT_MS = 120_000;
const PROMPT_MIN_LENGTH = 20;
const PROMPT_MAX_LENGTH = 3000;

function GenerateDeckPageContent() {
    const { data: session } = useSession();
    const router = useRouter();
    const searchParams = useSearchParams();
    const rawDeckId = searchParams.get("deckId");

    const [prompt, setPrompt] = useState("");
    const [regenerationDeckId, setRegenerationDeckId] = useState<string | null>(null);
    const [regenerationDeckName, setRegenerationDeckName] = useState<string | null>(null);
    const [isLoadingRegenerationDeckName, setIsLoadingRegenerationDeckName] = useState(false);
    const [availableSetCodes, setAvailableSetCodes] = useState<string[]>([]);
    const [selectedSetCodes, setSelectedSetCodes] = useState<string[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingSetCodes, setIsLoadingSetCodes] = useState(true);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    const [remainingQuota, setRemainingQuota] = useState<number | null>(null);
    const [isLoadingQuota, setIsLoadingQuota] = useState(true);
    const [generationError, setGenerationError] = useState<string | null>(null);
    const [generationStartedAt, setGenerationStartedAt] = useState<number | null>(null);

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

    const pollBuildStatus = useCallback((newTaskId: string) => {
        const interval = setInterval(async () => {
            if (generationStartedAt && Date.now() - generationStartedAt > BUILD_STATUS_TIMEOUT_MS) {
                clearInterval(interval);
                setIsGenerating(false);
                setGenerationError("Generation is taking longer than expected. Please try again in a moment.");
                return;
            }

            try {
                const statusResponse = await backendFetch(session, `/api/app/ai/deck/build_status/${newTaskId}/`);
                if (!statusResponse.ok) {
                    throw new Error("Failed to fetch build status");
                }

                const statusData = (await statusResponse.json()) as { status: string; deck_id: string };
                setStatus(statusData.status);

                if (statusData.status === "COMPLETED") {
                    clearInterval(interval);
                    setIsGenerating(false);
                    setGenerationStartedAt(null);
                    router.push(`/decks/${statusData.deck_id}`);
                    return;
                }

                if (statusData.status === "FAILED") {
                    clearInterval(interval);
                    setIsGenerating(false);
                    setGenerationStartedAt(null);
                    setGenerationError("Deck generation failed. Please revise your prompt and try again.");
                }
            } catch (error) {
                console.error("Error polling build status:", error);
                clearInterval(interval);
                setIsGenerating(false);
                setGenerationStartedAt(null);
                setGenerationError("Could not fetch generation status. Please try again.");
            }
        }, 2500);

        return interval;
    }, [generationStartedAt, router, session]);

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

    useEffect(() => {
        if (!taskId) {
            return;
        }

        const interval = pollBuildStatus(taskId);
        return () => clearInterval(interval);
    }, [taskId, pollBuildStatus]);

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
        setStatus("PENDING");
        setGenerationStartedAt(Date.now());

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
                throw new Error(await parseApiError(response, "Failed to start deck generation"));
            }

            const data = (await response.json()) as { task_id: string };
            setTaskId(data.task_id);
            setRemainingQuota((current) => {
                if (current === null) {
                    return current;
                }

                return Math.max(0, current - 1);
            });
        } catch (error) {
            console.error("Error generating deck:", error);
            setIsGenerating(false);
            setGenerationStartedAt(null);
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
                                        <p className="text-xs text-muted-foreground">You can deselect all set codes, but generation requires at least one selected set code.</p>
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
                            {status ? <p className="text-sm text-muted-foreground">Current status: {status}</p> : null}
                            {generationError ? <p className="text-sm">{generationError}</p> : null}
                            {taskId ? <p className="text-xs text-muted-foreground">Task ID: {taskId}</p> : null}
                        </CardContent>
                    </Card>
                </div>
            </main>
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
