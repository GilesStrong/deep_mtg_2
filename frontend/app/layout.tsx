import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import favicon from "./favicon.png";
import { LegalFooter } from "@/components/legal-footer";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Deep MTG",
  description: "AI-powered Magic: The Gathering deck builder",
  icons: {
    icon: [{ url: favicon.src, type: "image/png" }],
    shortcut: [{ url: favicon.src, type: "image/png" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen flex flex-col">
            <main className="flex-1">{children}</main>
            <LegalFooter />
          </div>
        </Providers>
      </body>
    </html>
  );
}
