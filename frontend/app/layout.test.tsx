import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const { mockProviders } = vi.hoisted(() => ({
    mockProviders: vi.fn(),
}));

vi.mock("next/font/google", () => ({
    Inter: vi.fn(() => ({ className: "mock-inter" })),
}));

vi.mock("@/app/providers", () => ({
    Providers: ({ children }: { children: React.ReactNode }) => {
        mockProviders();
        return <div data-testid="providers">{children}</div>;
    },
}));

vi.mock("@/app/favicon.png", () => ({
    default: {
        src: "/favicon.png",
    },
}));

import RootLayout, { metadata } from "@/app/layout";

describe("RootLayout", () => {
    it("wraps children with Providers and sets html lang/body class", () => {
        const { container } = render(
            <RootLayout>
                <main>Dashboard Content</main>
            </RootLayout>,
        );

        expect(screen.getByTestId("providers")).toBeInTheDocument();
        expect(screen.getByText("Dashboard Content")).toBeInTheDocument();
        expect(mockProviders).toHaveBeenCalledTimes(1);

        const html = container.querySelector("html");
        const body = container.querySelector("body");

        expect(html).toHaveAttribute("lang", "en");
        expect(body).toHaveClass("mock-inter");
    });

    it("exports expected metadata", () => {
        expect(metadata.title).toBe("Deep MTG");
        expect(metadata.description).toBe("AI-powered Magic: The Gathering deck builder");
        expect(metadata.icons).toEqual({
            icon: [{ url: "/favicon.png", type: "image/png" }],
            shortcut: [{ url: "/favicon.png", type: "image/png" }],
        });
    });
});
