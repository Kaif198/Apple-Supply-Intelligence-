"use client";

import * as React from "react";
import * as d3 from "d3";
import { cn } from "@/lib/utils";

/**
 * Inline sparkline for KPI tiles and list rows.
 * Declarative SVG with optional hover crosshair + tooltip.
 */

interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
  strokeClassName?: string;
  fillClassName?: string;
  showLast?: boolean;
  formatValue?: (v: number) => string;
  tooltipLabel?: string;
  className?: string;
}

export function Sparkline({
  values,
  width = 96,
  height = 28,
  strokeClassName = "stroke-fg-muted",
  fillClassName,
  showLast = false,
  formatValue = (v) => v.toFixed(2),
  tooltipLabel,
  className,
}: SparklineProps) {
  const [hover, setHover] = React.useState<{ x: number; y: number; value: number } | null>(null);

  if (!values || values.length < 2) {
    return <div className={cn("h-7 w-24", className)} aria-hidden />;
  }

  const pad = 2;
  const xScale = d3.scaleLinear().domain([0, values.length - 1]).range([pad, width - pad]);
  const [min, max] = d3.extent(values) as [number, number];
  const yScale = d3
    .scaleLinear()
    .domain(min === max ? [min - 1, max + 1] : [min, max])
    .range([height - pad, pad]);

  const lineGen = d3
    .line<number>()
    .x((_, i) => xScale(i))
    .y((v) => yScale(v))
    .curve(d3.curveMonotoneX);

  const areaGen = fillClassName
    ? d3
        .area<number>()
        .x((_, i) => xScale(i))
        .y0(height - pad)
        .y1((v) => yScale(v))
        .curve(d3.curveMonotoneX)
    : null;

  const linePath = lineGen(values) ?? "";
  const areaPath = areaGen ? areaGen(values) ?? "" : null;
  const last = values[values.length - 1];

  function handleMouseMove(e: React.MouseEvent<SVGSVGElement>) {
    const svgRect = e.currentTarget.getBoundingClientRect();
    const relX = e.clientX - svgRect.left;
    const idx = Math.max(0, Math.min(values.length - 1, Math.round((relX / width) * (values.length - 1))));
    const v = values[idx];
    if (v == null) return;
    setHover({ x: xScale(idx), y: yScale(v), value: v });
  }

  return (
    <div className={cn("relative inline-block", className)} style={{ width, height }}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="overflow-visible"
        role="img"
        aria-label={tooltipLabel ? `${tooltipLabel} sparkline` : "Trend sparkline"}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHover(null)}
      >
        {areaPath && <path d={areaPath} className={cn(fillClassName, "fill-current opacity-40")} />}
        <path d={linePath} fill="none" strokeWidth={1.25} className={cn(strokeClassName)} />

        {hover && (
          <g className="pointer-events-none">
            <line
              x1={hover.x}
              x2={hover.x}
              y1={pad}
              y2={height - pad}
              strokeWidth={1}
              strokeDasharray="2 2"
              className="stroke-fg-muted"
            />
            <circle cx={hover.x} cy={hover.y} r={2.5} className={cn(strokeClassName, "fill-current")} />
          </g>
        )}

        {showLast && last !== undefined && !hover && (
          <circle
            cx={xScale(values.length - 1)}
            cy={yScale(last)}
            r={1.75}
            className={cn(strokeClassName, "fill-current")}
          />
        )}
      </svg>

      {hover && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded border border-border-subtle bg-bg-elevated/95 px-1.5 py-1 text-[10px] leading-tight shadow-md backdrop-blur-md tabular-nums text-fg whitespace-nowrap"
          style={{ left: hover.x, top: hover.y - 6 }}
        >
          {tooltipLabel && <span className="text-fg-muted mr-1">{tooltipLabel}</span>}
          {formatValue(hover.value)}
        </div>
      )}
    </div>
  );
}
