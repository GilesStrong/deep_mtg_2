import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Label } from "@/components/ui/label";

describe("Label", () => {
    it("labels its associated control", async () => {
        const user = userEvent.setup();

        render(
            <div>
                <Label htmlFor="deck-name">Deck Name</Label>
                <input id="deck-name" />
            </div>,
        );

        await user.click(screen.getByText("Deck Name"));

        expect(screen.getByLabelText("Deck Name")).toHaveFocus();
    });
});
