import { describe, expect, it } from "vitest";
import {
  fmtBps,
  fmtCurrency,
  fmtCurrencyCompact,
  fmtDelta,
  fmtNumber,
  fmtPercent,
  signalClass,
} from "./format";

/**
 * Formatters drive every number users see. A regression here shows up
 * as "$2,500,000,000" in a dashboard where we wanted "$2.5B", so these
 * tests guard the exact output shape.
 */

describe("fmtNumber", () => {
  it("defaults to 2 decimals", () => {
    expect(fmtNumber(1234.5)).toBe("1,234.50");
  });

  it("honors custom precision", () => {
    expect(fmtNumber(0.123456, 4)).toBe("0.1235");
  });

  it("handles zero and negative values", () => {
    expect(fmtNumber(0)).toBe("0.00");
    expect(fmtNumber(-42.1)).toBe("-42.10");
  });
});

describe("fmtCurrency", () => {
  it("uses USD with thousands separators", () => {
    expect(fmtCurrency(1234.5)).toBe("$1,234.50");
  });
});

describe("fmtCurrencyCompact", () => {
  it("produces compact scale for billions", () => {
    expect(fmtCurrencyCompact(2_600_000_000)).toMatch(/\$2\.6B/);
  });

  it("produces compact scale for trillions", () => {
    expect(fmtCurrencyCompact(3_200_000_000_000)).toMatch(/\$3\.2T/);
  });
});

describe("fmtPercent", () => {
  it("converts a fraction to percent with default precision", () => {
    expect(fmtPercent(0.1234)).toBe("12.34%");
  });

  it("rounds as expected", () => {
    expect(fmtPercent(0.025, 1)).toBe("2.5%");
  });
});

describe("fmtDelta", () => {
  it("prepends a plus sign for positive values", () => {
    expect(fmtDelta(0.012)).toBe("+1.20%");
  });

  it("leaves negative values with their intrinsic sign", () => {
    expect(fmtDelta(-0.005)).toBe("-0.50%");
  });

  it("has no sign for zero", () => {
    expect(fmtDelta(0)).toBe("0.00%");
  });
});

describe("fmtBps", () => {
  it("rounds a bps value and prepends sign", () => {
    expect(fmtBps(120.4)).toBe("+120 bps");
  });

  it("converts a fractional delta when asFraction is true", () => {
    expect(fmtBps(0.012, true)).toBe("+120 bps");
  });

  it("handles negatives", () => {
    expect(fmtBps(-37)).toBe("-37 bps");
  });
});

describe("signalClass", () => {
  it("maps positive, negative, and zero to distinct tokens", () => {
    expect(signalClass(0.5)).toBe("text-signal-pos");
    expect(signalClass(-0.5)).toBe("text-signal-neg");
    expect(signalClass(0)).toBe("text-fg-muted");
  });
});
