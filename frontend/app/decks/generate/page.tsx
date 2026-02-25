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

function GenerateDeckPageContent() {
    const { data: session } = useSession();
    const router = useRouter();
    const searchParams = useSearchParams();
    const deckId = searchParams.get("deckId");

    const [prompt, setPrompt] = useState("");
    const [availableSetCodes, setAvailableSetCodes] = useState<string[]>([]);
    const [selectedSetCodes, setSelectedSetCodes] = useState<string[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingSetCodes, setIsLoadingSetCodes] = useState(true);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);

    const userInitials =
        session?.user?.name
            ?.split(" ")
            .map((n) => n[0])
            .join("")
            .toUpperCase() || "U";

    const pollBuildStatus = useCallback((newTaskId: string) => {
        const interval = setInterval(async () => {
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
                    router.push(`/decks/${statusData.deck_id}`);
                    return;
                }

                if (statusData.status === "FAILED") {
                    clearInterval(interval);
                    setIsGenerating(false);
                }
            } catch (error) {
                console.error("Error polling build status:", error);
                clearInterval(interval);
                setIsGenerating(false);
            }
        }, 2500);

        return interval;
    }, [router, session]);

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
        if (!prompt.trim() || selectedSetCodes.length === 0) {
            return;
        }

        setIsGenerating(true);
        setStatus("PENDING");

        try {
            const payload: { prompt: string; set_codes: string[]; deck_id?: string } = {
                prompt,
                set_codes: selectedSetCodes,
            };

            if (deckId) {
                payload.deck_id = deckId;
            }

            const response = await backendFetch(session, "/api/app/ai/deck/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error("Failed to start deck generation");
            }

            const data = (await response.json()) as { task_id: string };
            setTaskId(data.task_id);
        } catch (error) {
            console.error("Error generating deck:", error);
            setIsGenerating(false);
        }
    };

    const handleSignOut = async () => {
        clearBackendTokens();
        await signOut({ callbackUrl: "/login" });
    };

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
                            <CardTitle>{deckId ? "Regenerate Deck" : "Generate Deck"}</CardTitle>
                            <CardDescription>
                                {deckId
                                    ? "Submit a new prompt to rebuild this existing deck."
                                    : "Describe the deck you want and start a generation task."}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {deckId ? (
                                <p className="text-sm text-muted-foreground">Target deck: {deckId}</p>
                            ) : null}
                            <div className="space-y-2">
                                <Label htmlFor="prompt">Prompt</Label>
                                <Textarea
                                    id="prompt"
                                    placeholder="A blue-red spellslinger deck with strong instant-speed interaction..."
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    rows={5}
                                    disabled={isGenerating}
                                />
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
                                disabled={!prompt.trim() || isGenerating || isLoadingSetCodes || selectedSetCodes.length === 0}
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
                            {status ? <p className="text-sm text-muted-foreground">Current status: {status}</p> : null}
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
        <Suspense fallback={<div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100" />}>
            <GenerateDeckPageContent />
        </Suspense>
    );
}
