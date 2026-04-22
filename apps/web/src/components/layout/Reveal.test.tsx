import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Reveal } from "./Reveal";

/**
 * Reveal wraps scroll-in content. In the test environment the mocked
 * IntersectionObserver never fires, so the component's graceful fallback
 * (rendered == visible when reduced-motion or no IO) is what we verify.
 */

describe("Reveal", () => {
  it("renders its children", () => {
    render(
      <Reveal>
        <p>hello</p>
      </Reveal>,
    );
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("applies a user-supplied className on the wrapper", () => {
    const { container } = render(
      <Reveal className="custom-wrap">
        <span>child</span>
      </Reveal>,
    );
    expect((container.firstChild as HTMLElement).className).toMatch(
      /custom-wrap/,
    );
  });
});
