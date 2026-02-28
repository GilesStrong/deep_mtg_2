import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

describe("Card components", () => {
    it("renders card structure and content", () => {
        render(
            <Card data-testid="card-root">
                <CardHeader>
                    <CardTitle>Deck Title</CardTitle>
                    <CardDescription>Deck Description</CardDescription>
                </CardHeader>
                <CardContent>Body</CardContent>
                <CardFooter>Footer</CardFooter>
            </Card>,
        );

        expect(screen.getByTestId("card-root")).toBeInTheDocument();
        expect(screen.getByText("Deck Title")).toBeInTheDocument();
        expect(screen.getByText("Deck Description")).toBeInTheDocument();
        expect(screen.getByText("Body")).toBeInTheDocument();
        expect(screen.getByText("Footer")).toBeInTheDocument();
    });
});
