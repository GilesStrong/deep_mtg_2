import { describe, expect, it, vi } from "vitest";

const { mockRedirect } = vi.hoisted(() => ({
    mockRedirect: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    redirect: mockRedirect,
}));

import Home from "@/app/page";

describe("Home page", () => {
    it("redirects to dashboard", () => {
        Home();

        expect(mockRedirect).toHaveBeenCalledWith("/dashboard");
    });
});
