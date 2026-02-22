"use client";

import { useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Loader2 } from "lucide-react";

export default function DashboardPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [format, setFormat] = useState("commander");
  const [isGenerating, setIsGenerating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);

  const handleGenerateDeck = async () => {
    if (!prompt.trim()) return;

    setIsGenerating(true);
    setJobId(null);
    setJobStatus(null);

    try {
      const response = await fetch("/api/decks/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, format }),
      });

      if (!response.ok) throw new Error("Failed to generate deck");

      const data = await response.json();
      setJobId(data.job_id);
      pollJobStatus(data.job_id);
    } catch (error) {
      console.error("Error generating deck:", error);
      setIsGenerating(false);
    }
  };

  const pollJobStatus = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${id}`);
        if (!response.ok) throw new Error("Failed to fetch job status");

        const data = await response.json();
        setJobStatus(data);

        if (data.status === "succeeded" && data.deck_id) {
          clearInterval(interval);
          setIsGenerating(false);
          router.push(`/decks/${data.deck_id}`);
        } else if (data.status === "failed") {
          clearInterval(interval);
          setIsGenerating(false);
        }
      } catch (error) {
        console.error("Error polling job:", error);
        clearInterval(interval);
        setIsGenerating(false);
      }
    }, 1500);
  };

  const userInitials = session?.user?.name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase() || "U";

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
        <div className="max-w-2xl mx-auto space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Generate a New Deck</CardTitle>
              <CardDescription>
                Describe the deck you want and our AI will create it for you
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="prompt">Deck Description</Label>
                <Textarea
                  id="prompt"
                  placeholder="E.g., A blue-red spellslinger deck focused on instant and sorcery spells..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={4}
                  disabled={isGenerating}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="format">Format</Label>
                <Select value={format} onValueChange={setFormat} disabled={isGenerating}>
                  <SelectTrigger id="format">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="commander">Commander</SelectItem>
                    <SelectItem value="modern">Modern</SelectItem>
                    <SelectItem value="standard">Standard</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleGenerateDeck}
                disabled={!prompt.trim() || isGenerating}
                className="w-full"
                size="lg"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  "Generate Deck"
                )}
              </Button>
            </CardContent>
          </Card>

          {isGenerating && jobStatus && (
            <Card>
              <CardHeader>
                <CardTitle>Generation Progress</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{jobStatus.message}</span>
                  <span className="text-muted-foreground">{jobStatus.progress}%</span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${jobStatus.progress}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Status: {jobStatus.status}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
