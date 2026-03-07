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

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function TermsPage() {
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
                <h1 className="text-3xl font-bold">Terms of Service</h1>

                <Card>
                    <CardHeader>
                        <CardTitle>Acceptable use</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>- Use the service lawfully and do not attempt abuse, scraping, or disruption.</p>
                        <p>- You are responsible for activity performed through your authenticated account.</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Service behavior</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>- Deck generation output is AI-assisted and may be incomplete or inaccurate.</p>
                        <p>- Availability and features may change over time without prior notice.</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Account lifecycle</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm text-muted-foreground">
                        <p>- Accounts may be limited or blocked for repeated policy violations.</p>
                        <p>- You may export or delete your account data from Dashboard → Account.</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
