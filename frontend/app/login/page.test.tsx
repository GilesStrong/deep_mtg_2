import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { mockUseSearchParams, mockSignIn } = vi.hoisted(() => ({
    mockUseSearchParams: vi.fn(),
    mockSignIn: vi.fn(),
}));

vi.mock("next/navigation", () => ({
    useSearchParams: mockUseSearchParams,
}));

vi.mock("next-auth/react", () => ({
    signIn: mockSignIn,
}));

import LoginPage from "@/app/login/page";

describe("LoginPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    it("shows auth error message when present in query params", () => {
        mockUseSearchParams.mockReturnValue({
            get: (key: string) => (key === "error" ? "OAuthAccountNotLinked" : null),
        });

        render(<LoginPage />);

        expect(screen.getByText("OAuthAccountNotLinked")).toBeInTheDocument();
    });

    it("calls signIn with Google provider when button is clicked", async () => {
        const user = userEvent.setup();
        mockUseSearchParams.mockReturnValue({ get: () => null });

        render(<LoginPage />);
        await user.click(screen.getByRole("button", { name: "Sign in with Google" }));

        expect(mockSignIn).toHaveBeenCalledWith("google", { callbackUrl: "/dashboard" });
    });
});
