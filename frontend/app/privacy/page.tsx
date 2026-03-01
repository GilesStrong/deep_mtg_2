import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PrivacyPage() {
    return (
        <div className="flex-1 bg-gradient-to-br from-slate-50 to-slate-100 px-4 py-10">
            <header className="border-b bg-white/80 backdrop-blur-sm -mx-4 -mt-10 mb-10">
                <div className="container mx-auto flex items-center justify-between px-4 py-4">
                    <p className="text-2xl font-bold">Deep MTG</p>
                    <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
                        Back to Dashboard
                    </Link>
                </div>
            </header>
            <div className="mx-auto max-w-3xl space-y-6">
                <h1 className="text-3xl font-bold">Privacy Policy</h1>

                <Card>
                    <CardHeader>
                        <CardTitle>What we collect</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>- Your Google account identifier and verification status for sign-in.</p>
                        <p>- Deck content and related generation history you create in the app.</p>
                        <p>- Refresh token metadata (user agent, IP, timestamps) for account security.</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>How we use data</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>- To authenticate you and protect your account.</p>
                        <p>- To generate, store, and serve your deck-building results.</p>
                        <p>- To enforce abuse-prevention and platform policy safeguards.</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Your controls</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>- Export your account data at any time from Dashboard → Account.</p>
                        <p>- Permanently delete your account and associated data from Dashboard → Account.</p>
                        <p>- Contact support for questions or requests via the Support page.</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
