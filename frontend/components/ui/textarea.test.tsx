import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Textarea } from "@/components/ui/textarea";

describe("Textarea", () => {
    it("renders placeholder and accepts typed value", async () => {
        const user = userEvent.setup();

        render(<Textarea placeholder="Describe your deck idea" />);

        const textarea = screen.getByPlaceholderText("Describe your deck idea");
        await user.type(textarea, "Aggro deck with haste creatures");

        expect(textarea).toHaveValue("Aggro deck with haste creatures");
    });
});
