import Link from "next/link";

export function LegalFooter() {
  return (
    <footer className="border-t bg-white/80">
      <div className="container mx-auto flex flex-wrap items-center justify-center gap-x-6 gap-y-2 px-4 py-4 text-sm text-muted-foreground">
        <Link href="/privacy" className="hover:text-foreground">
          Privacy Policy
        </Link>
        <Link href="/terms" className="hover:text-foreground">
          Terms of Service
        </Link>
        <Link href="/support" className="hover:text-foreground">
          Support & Contact
        </Link>
      </div>
    </footer>
  );
}
