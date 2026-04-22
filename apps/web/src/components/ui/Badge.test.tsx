import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./Badge";

/**
 * Badge is used everywhere severity, tier, and status appear. A break
 * here usually means a Tailwind class was renamed in the design system.
 */

describe("Badge", () => {
  it("renders its children", () => {
    render(<Badge>critical</Badge>);
    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  it("applies the neutral variant by default", () => {
    render(<Badge>default</Badge>);
    const el = screen.getByText("default");
    expect(el.className).toMatch(/text-fg-muted/);
  });

  it("applies the severity variant classes", () => {
    render(<Badge variant="critical">breach</Badge>);
    const el = screen.getByText("breach");
    expect(el.className).toMatch(/severity-critical/);
  });

  it("merges user-supplied className", () => {
    render(
      <Badge variant="accent" className="custom-class">
        hello
      </Badge>,
    );
    const el = screen.getByText("hello");
    expect(el.className).toMatch(/custom-class/);
    expect(el.className).toMatch(/accent/);
  });

  it("is a <span> so it can nest inside flex rows", () => {
    const { container } = render(<Badge>x</Badge>);
    expect(container.firstChild?.nodeName).toBe("SPAN");
  });
});
