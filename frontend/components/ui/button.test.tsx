import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/components/ui/button";

describe("Button", () => {
    it("renders label text", () => {
        render(<Button>Build Deck</Button>);

        expect(
            screen.getByRole("button", { name: "Build Deck" }),
        ).toBeInTheDocument();
    });

    it("calls onClick when pressed", async () => {
        const user = userEvent.setup();
        const onClick = vi.fn();

        render(<Button onClick={onClick}>Generate</Button>);
        await user.click(screen.getByRole("button", { name: "Generate" }));

        expect(onClick).toHaveBeenCalledTimes(1);
    });
});
