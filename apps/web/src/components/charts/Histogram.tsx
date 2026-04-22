"use client";

import * as React from "react";
import * as d3 from "d3";
import { cn } from "@/lib/utils";

interface HistogramProps {
  samples: number[];
  binCount?: number;
  markers?: { value: number; label: string; strokeClassName?: string }[];
  height?: number;
  format?: (v: number) => string;
  ariaLabel?: string;
  className?: string;
}

interface HistTooltip {
  x: number;
  y: number;
  x0: number;
  x1: number;
  count: number;
}

const MARGIN = { top: 16, right: 16, bottom: 28, left: 40 };

export function Histogram({
  samples,
  binCount = 40,
  markers = [],
  height = 200,
  format = (v) => v.toFixed(0),
  ariaLabel = "Histogram",
  className,
}: HistogramProps) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [width, setWidth] = React.useState(520);
  const [tooltip, setTooltip] = React.useState<HistTooltip | null>(null);
  const [hoveredIdx, setHoveredIdx] = React.useState<number | null>(null);

  React.useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const ro = new ResizeObserver(([entry]) => {
      if (entry) setWidth(Math.max(260, entry.contentRect.width));
    });
    ro.observe(node);
    return () => ro.disconnect();
  }, []);

  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

  if (!samples.length) {
    return <div ref={ref} className={cn("h-[200px]", className)} />;
  }

  const [min, max] = d3.extent(samples) as [number, number];
  const xScale = d3.scaleLinear().domain([min, max]).nice().range([0, innerW]);
  const binner = d3
    .bin<number, number>()
    .domain(xScale.domain() as [number, number])
    .thresholds(binCount);
  const bins = binner(samples);
  const yMax = d3.max(bins, (b) => b.length) ?? 1;
  const yScale = d3.scaleLinear().domain([0, yMax]).range([innerH, 0]);

  function handleBarEnter(e: React.MouseEvent<SVGRectElement>, idx: number) {
    if (!ref.current) return;
    const barRect = e.currentTarget.getBoundingClientRect();
    const containerRect = ref.current.getBoundingClientRect();
    const b = bins[idx]!;
    setHoveredIdx(idx);
    setTooltip({
      x: barRect.left + barRect.width / 2 - containerRect.left,
      y: barRect.top - containerRect.top,
      x0: b.x0!,
      x1: b.x1!,
      count: b.length,
    });
  }

  return (
    <div ref={ref} className={cn("relative w-full", className)}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {/* Horizontal gridlines */}
          {yScale.ticks(4).map((t) => (
            <line
              key={`yg-${t}`}
              x1={0}
              x2={innerW}
              y1={yScale(t)}
              y2={yScale(t)}
              className="stroke-border-subtle"
              strokeDasharray="2 3"
            />
          ))}

          {/* Bars */}
          {bins.map((b, idx) => {
            const x0 = xScale(b.x0!);
            const x1 = xScale(b.x1!);
            const w = Math.max(1, x1 - x0 - 1);
            const yPos = yScale(b.length);
            return (
              <rect
                key={idx}
                x={x0}
                y={yPos}
                width={w}
                height={innerH - yPos}
                rx={2}
                className={cn(
                  "cursor-default transition-colors duration-100",
                  hoveredIdx === idx ? "fill-accent/90" : "fill-accent/60",
                )}
                onMouseEnter={(e) => handleBarEnter(e, idx)}
                onMouseLeave={() => { setTooltip(null); setHoveredIdx(null); }}
              />
            );
          })}

          {/* X axis ticks */}
          {xScale.ticks(5).map((t) => (
            <text
              key={`xt-${t}`}
              x={xScale(t)}
              y={innerH + 16}
              textAnchor="middle"
              className="fill-fg-subtle font-mono text-[10px] tracking-wider"
            >
              {format(t)}
            </text>
          ))}

          {/* Marker lines (mean / VaR / CVaR) */}
          {markers.map((m) => {
            const mx = xScale(m.value);
            if (mx < 0 || mx > innerW) return null;
            return (
              <g key={`marker-${m.label}`} className="pointer-events-none">
                <line
                  x1={mx}
                  x2={mx}
                  y1={0}
                  y2={innerH}
                  strokeWidth={1.25}
                  strokeDasharray="3 3"
                  className={cn("stroke-fg", m.strokeClassName)}
                />
                <text
                  x={mx}
                  y={-4}
                  textAnchor="middle"
                  className={cn(
                    "font-mono text-[10px] uppercase tracking-[0.14em] fill-fg-subtle",
                    m.strokeClassName?.replace("stroke-", "fill-"),
                  )}
                >
                  {m.label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg border border-border-subtle bg-bg-elevated/95 px-2.5 py-1.5 text-[11px] leading-tight shadow-lg backdrop-blur-md"
          style={{ left: tooltip.x, top: tooltip.y - 6 }}
        >
          <div className="font-mono tabular-nums text-fg font-semibold">
            {format(tooltip.x0)} – {format(tooltip.x1)}
          </div>
          <div className="text-fg-muted">
            {tooltip.count} trials
            {samples.length > 0 && (
              <span className="ml-1.5 text-fg-subtle">
                · {((tooltip.count / samples.length) * 100).toFixed(1)}%
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
