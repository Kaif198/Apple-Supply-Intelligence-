import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Button } from "./Button";

/**
 * Button covers both the primary accent action and the `asChild` Slot
 * pattern we use for link-as-button throughout the nav.
 */

describe("Button", () => {
  it("renders as a <button> by default", () => {
    render(<Button>Run</Button>);
    const el = screen.getByRole("button", { name: "Run" });
    expect(el.tagName).toBe("BUTTON");
  });

  it("fires onClick when clicked", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    fireEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("applies the accent variant when variant='default'", () => {
    render(<Button variant="default">Primary</Button>);
    const el = screen.getByRole("button", { name: "Primary" });
    expect(el.className).toMatch(/bg-accent/);
  });

  it("respects the disabled attribute", () => {
    render(<Button disabled>Off</Button>);
    const el = screen.getByRole("button", { name: "Off" });
    expect(el).toBeDisabled();
  });

  it("polymorphs into the child element when asChild is true", () => {
    render(
      <Button asChild>
        <a href="/docs">Docs</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "Docs" });
    expect(link.tagName).toBe("A");
    expect(link).toHaveAttribute("href", "/docs");
  });
});
