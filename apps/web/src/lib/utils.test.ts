import { describe, expect, it } from "vitest";
import { clamp, cn, fingerprint, lerp } from "./utils";

/**
 * Pure helper tests — no DOM, no async, very fast.
 */

describe("cn", () => {
  it("joins simple class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("drops falsy values", () => {
    expect(cn("a", false && "b", null, undefined, "c")).toBe("a c");
  });

  it("resolves conflicting Tailwind utilities via tailwind-merge", () => {
    // If twMerge is wired correctly, the later class wins.
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
});

describe("clamp", () => {
  it("returns the value when inside the range", () => {
    expect(clamp(5, 0, 10)).toBe(5);
  });

  it("clamps below the minimum", () => {
    expect(clamp(-3, 0, 10)).toBe(0);
  });

  it("clamps above the maximum", () => {
    expect(clamp(12, 0, 10)).toBe(10);
  });
});

describe("lerp", () => {
  it("interpolates the midpoint", () => {
    expect(lerp(0, 10, 0.5)).toBe(5);
  });

  it("returns the endpoints for t=0 and t=1", () => {
    expect(lerp(2, 8, 0)).toBe(2);
    expect(lerp(2, 8, 1)).toBe(8);
  });
});

describe("fingerprint", () => {
  it("is deterministic for equivalent objects", () => {
    expect(fingerprint({ a: 1, b: 2 })).toBe(fingerprint({ b: 2, a: 1 }));
  });

  it("differs for different values", () => {
    expect(fingerprint({ a: 1 })).not.toBe(fingerprint({ a: 2 }));
  });

  it("tolerates null and undefined", () => {
    expect(() => fingerprint(null)).not.toThrow();
    expect(() => fingerprint(undefined)).not.toThrow();
  });
});
