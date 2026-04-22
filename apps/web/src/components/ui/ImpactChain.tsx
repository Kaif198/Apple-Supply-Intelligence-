"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { fmtNumber, fmtPercent } from "@/lib/format";

// Apple FY2024 constants for EPS / price derivation
const APPLE_REVENUE_B = 391;
const APPLE_SHARES_B = 15.4;
const APPLE_PE = 31;

export interface ImpactChainValues {
  eventTitle?: string;
  supplierName?: string;
  commodity?: string;
  marginDeltaBps?: number | null;
  epsDelta?: number | null;
  priceDelta?: number | null;
}

interface ImpactChainProps {
  values: ImpactChainValues;
  className?: string;
}

function deriveEps(marginDeltaBps: number): number {
  return (marginDeltaBps / 10_000) * APPLE_REVENUE_B / APPLE_SHARES_B;
}

function derivePrice(epsDelta: number): number {
  return epsDelta * APPLE_PE;
}

interface StageProps {
  label: string;
  value: string;
  tone?: "neg" | "pos" | "neutral";
}

function Stage({ label, value, tone = "neutral" }: StageProps) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className="text-[9px] font-medium uppercase tracking-[0.12em] text-fg-subtle">
        {label}
      </span>
      <span
        className={cn(
          "rounded-full px-2.5 py-0.5 text-[11px] font-semibold tabular-nums",
          tone === "neg" && "bg-severity-high/15 text-severity-high",
          tone === "pos" && "bg-signal-pos/15 text-signal-pos",
          tone === "neutral" && "bg-bg-raised text-fg",
        )}
      >
        {value}
      </span>
    </div>
  );
}

function Arrow() {
  return (
    <svg
      width="16"
      height="10"
      viewBox="0 0 16 10"
      className="shrink-0 fill-none stroke-border-strong"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M1 5h12M9 1l4 4-4 4" />
    </svg>
  );
}

export function ImpactChain({ values, className }: ImpactChainProps) {
  const { eventTitle, supplierName, commodity, marginDeltaBps } = values;

  if (marginDeltaBps == null && !eventTitle && !supplierName) return null;

  const bps = marginDeltaBps ?? 0;
  const eps = values.epsDelta ?? deriveEps(bps);
  const price = values.priceDelta ?? derivePrice(eps);
  const tone = bps < 0 ? "neg" : "pos";

  const stages: StageProps[] = [];

  if (eventTitle) stages.push({ label: "Event", value: eventTitle.slice(0, 22) + (eventTitle.length > 22 ? "…" : ""), tone: "neg" });
  if (supplierName) stages.push({ label: "Supplier", value: supplierName, tone: "neg" });
  if (commodity) stages.push({ label: "Input", value: commodity.replace(/_/g, " "), tone: "neutral" });

  if (marginDeltaBps != null) {
    stages.push({
      label: "Gross margin",
      value: `${bps > 0 ? "+" : ""}${fmtNumber(bps, 0)} bps`,
      tone,
    });
    stages.push({
      label: "EPS Δ",
      value: `${eps > 0 ? "+" : ""}$${Math.abs(eps).toFixed(2)}`,
      tone,
    });
    stages.push({
      label: "Fair value Δ",
      value: `${price > 0 ? "+" : ""}$${fmtNumber(price, 1)}`,
      tone,
    });
  }

  if (!stages.length) return null;

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {stages.map((s, i) => (
        <React.Fragment key={i}>
          <Stage {...s} />
          {i < stages.length - 1 && <Arrow />}
        </React.Fragment>
      ))}
    </div>
  );
}
