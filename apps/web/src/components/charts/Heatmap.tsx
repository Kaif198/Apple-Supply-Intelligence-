"use client";

import * as React from "react";
import * as d3 from "d3";
import { cn } from "@/lib/utils";

interface HeatmapProps {
  rowLabels: string[];
  colLabels: string[];
  values: number[][];
  formatCell?: (v: number) => string;
  formatAxis?: (v: string) => string;
  center?: number;
  height?: number;
  ariaLabel?: string;
  className?: string;
}

interface HeatTooltip {
  x: number;
  y: number;
  row: string;
  col: string;
  value: number;
}

const MARGIN = { top: 8, right: 8, bottom: 32, left: 76 };

export function Heatmap({
  rowLabels,
  colLabels,
  values,
  formatCell = (v) => (Number.isFinite(v) ? v.toFixed(2) : "—"),
  formatAxis = (v) => v,
  center,
  height = 240,
  ariaLabel = "Heatmap",
  className,
}: HeatmapProps) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [width, setWidth] = React.useState(600);
  const [tooltip, setTooltip] = React.useState<HeatTooltip | null>(null);
  const [hoveredKey, setHoveredKey] = React.useState<string | null>(null);

  React.useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const ro = new ResizeObserver(([entry]) => {
      if (entry) setWidth(Math.max(320, entry.contentRect.width));
    });
    ro.observe(node);
    return () => ro.disconnect();
  }, []);

  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

  const flat = values.flat().filter((v) => Number.isFinite(v));
  const mid = center ?? (flat.length ? d3.median(flat)! : 0);
  const spread = Math.max(
    Math.abs((d3.max(flat) ?? mid) - mid),
    Math.abs(mid - (d3.min(flat) ?? mid)),
    1e-6,
  );

  const colScale = d3
    .scaleDiverging<string>()
    .domain([mid - spread, mid, mid + spread])
    .interpolator(d3.interpolateRdYlGn);

  const x = d3.scaleBand<string>().domain(colLabels).range([0, innerW]).padding(0.06);
  const y = d3.scaleBand<string>().domain(rowLabels).range([0, innerH]).padding(0.06);
  const cellW = x.bandwidth();
  const cellH = y.bandwidth();

  function handleCellEnter(
    e: React.MouseEvent<SVGRectElement>,
    i: number,
    j: number,
    value: number,
  ) {
    if (!ref.current) return;
    const cellRect = e.currentTarget.getBoundingClientRect();
    const containerRect = ref.current.getBoundingClientRect();
    setHoveredKey(`${i}-${j}`);
    setTooltip({
      x: cellRect.left + cellRect.width / 2 - containerRect.left,
      y: cellRect.top - containerRect.top,
      row: rowLabels[i] ?? "",
      col: colLabels[j] ?? "",
      value,
    });
  }

  return (
    <div ref={ref} className={cn("relative w-full", className)}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {values.map((row, i) =>
            row.map((value, j) => {
              const xs = x(colLabels[j]!) ?? 0;
              const ys = y(rowLabels[i]!) ?? 0;
              const isHovered = hoveredKey === `${i}-${j}`;
              return (
                <g key={`${i}-${j}`} transform={`translate(${xs},${ys})`}>
                  <rect
                    width={cellW}
                    height={cellH}
                    rx={3}
                    fill={Number.isFinite(value) ? colScale(value) : "transparent"}
                    stroke={isHovered ? "rgba(255,255,255,0.75)" : "none"}
                    strokeWidth={2}
                    className={cn(!Number.isFinite(value) && "fill-bg-inset", "cursor-default")}
                    onMouseEnter={(e) => handleCellEnter(e, i, j, value)}
                    onMouseLeave={() => { setTooltip(null); setHoveredKey(null); }}
                  />
                  <text
                    x={cellW / 2}
                    y={cellH / 2}
                    dy="0.32em"
                    textAnchor="middle"
                    className="pointer-events-none font-mono text-[10px] tabular-nums"
                    style={{ fill: Number.isFinite(value) ? "rgba(0,0,0,0.8)" : "hsl(var(--fg-muted))" }}
                  >
                    {formatCell(value)}
                  </text>
                </g>
              );
            }),
          )}

          {/* Column labels */}
          {colLabels.map((label) => (
            <text
              key={`col-${label}`}
              x={(x(label) ?? 0) + cellW / 2}
              y={innerH + 16}
              textAnchor="middle"
              className="fill-fg-subtle font-mono text-[10px] tracking-wider"
            >
              {formatAxis(label)}
            </text>
          ))}

          {/* Row labels */}
          {rowLabels.map((label) => (
            <text
              key={`row-${label}`}
              x={-8}
              y={(y(label) ?? 0) + cellH / 2}
              dy="0.32em"
              textAnchor="end"
              className="fill-fg-subtle font-mono text-[10px] tracking-wider"
            >
              {formatAxis(label)}
            </text>
          ))}
        </g>
      </svg>

      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg border border-border-subtle bg-bg-elevated/95 px-2.5 py-1.5 text-[11px] leading-tight shadow-lg backdrop-blur-md"
          style={{ left: tooltip.x, top: tooltip.y - 6 }}
        >
          <div className="font-mono tabular-nums text-fg font-semibold">
            {formatCell(tooltip.value)}
          </div>
          <div className="mt-0.5 text-fg-muted">
            {tooltip.row} → {tooltip.col}
          </div>
        </div>
      )}
    </div>
  );
}
