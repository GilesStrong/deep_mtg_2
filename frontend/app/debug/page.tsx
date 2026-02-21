export default function DebugPage() {
    return (
        <pre>{JSON.stringify({
            NEXTAUTH_URL: process.env.NEXTAUTH_URL ?? null,
            HAS_SECRET: Boolean(process.env.NEXTAUTH_SECRET),
            HAS_GOOGLE_ID: Boolean(process.env.GOOGLE_CLIENT_ID),
            HAS_GOOGLE_SECRET: Boolean(process.env.GOOGLE_CLIENT_SECRET),
        }, null, 2)}</pre>
    );
}
