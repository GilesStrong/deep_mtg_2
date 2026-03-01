import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? "support@deepmtg.local";

export default function SupportPage() {
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
                <h1 className="text-3xl font-bold">Support & Contact</h1>

                <Card>
                    <CardHeader>
                        <CardTitle>Contact support</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>For account or product issues, email us at:</p>
                        <p>
                            <a href={`mailto:${SUPPORT_EMAIL}`} className="font-medium text-foreground underline">
                                {SUPPORT_EMAIL}
                            </a>
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Account requests</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>- Data export is available in Dashboard → Account.</p>
                        <p>- Account deletion is available in Dashboard → Account.</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
