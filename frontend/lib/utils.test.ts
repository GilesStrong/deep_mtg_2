import { describe, expect, it } from "vitest";

import { cn } from "@/lib/utils";

describe("cn", () => {
    it("merges class names", () => {
        expect(cn("px-2", "font-bold")).toBe("px-2 font-bold");
    });

    it("resolves Tailwind conflicts with the last value", () => {
        expect(cn("px-2", "px-4", { hidden: false, block: true })).toBe(
            "px-4 block",
        );
    });
});
