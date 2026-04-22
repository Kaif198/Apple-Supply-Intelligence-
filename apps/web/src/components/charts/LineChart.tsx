"use client";

import * as React from "react";
import * as d3 from "d3";
import { cn } from "@/lib/utils";

export interface LineSeries {
  id: string;
  points: { ts: string | Date; value: number }[];
  strokeClassName?: string;
  dashed?: boolean;
  band?: { lower: number; upper: number }[];
  bandClassName?: string;
}

interface LineChartProps {
  series: LineSeries[];
  height?: number;
  yFormat?: (v: number) => string;
  yLabel?: string;
  xTicks?: number;
  yTicks?: number;
  ariaLabel?: string;
  className?: string;
}

interface LineTooltip {
  x: number;
  y: number;
  date: Date;
  entries: {
    id: string;
    value: number;
    prevValue: number | null;
    cy: number;
    strokeClassName?: string;
  }[];
}

const MARGIN = { top: 16, right: 16, bottom: 24, left: 44 };

export function LineChart({
  series,
  height = 220,
  yFormat = (v) => v.toFixed(2),
  yLabel,
  xTicks = 6,
  yTicks = 5,
  ariaLabel = "Line chart",
  className,
}: LineChartProps) {
  const ref = React.useRef<HTMLDivElement>(null);
  const svgRef = React.useRef<SVGSVGElement>(null);
  const [width, setWidth] = React.useState<number>(600);
  const [tooltip, setTooltip] = React.useState<LineTooltip | null>(null);

  React.useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const ro = new ResizeObserver(([entry]) => {
      if (entry) setWidth(Math.max(240, entry.contentRect.width));
    });
    ro.observe(node);
    return () => ro.disconnect();
  }, []);

  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

  const allPoints = series.flatMap((s) => s.points);
  if (allPoints.length === 0) {
    return <div ref={ref} className={cn("h-[220px]", className)} />;
  }

  const xDomain = d3.extent(allPoints, (p) => new Date(p.ts)) as [Date, Date];
  const yValues = allPoints.map((p) => p.value);
  const bandValues = series.flatMap((s) =>
    (s.band ?? []).flatMap((b) => [b.lower, b.upper]),
  );
  const yMin = Math.min(...yValues, ...bandValues);
  const yMax = Math.max(...yValues, ...bandValues);
  const yPad = Math.max((yMax - yMin) * 0.08, 1e-6);

  const xScale = d3.scaleTime().domain(xDomain).range([0, innerW]);
  const yScale = d3
    .scaleLinear()
    .domain([yMin - yPad, yMax + yPad])
    .nice()
    .range([innerH, 0]);

  const lineGen = d3
    .line<{ ts: string | Date; value: number }>()
    .x((p) => xScale(new Date(p.ts)))
    .y((p) => yScale(p.value))
    .curve(d3.curveMonotoneX);

  const bisect = d3.bisector<{ ts: string | Date; value: number }, Date>(
    (p) => new Date(p.ts),
  ).center;

  function handleMouseMove(e: React.MouseEvent<SVGRectElement>) {
    if (!svgRef.current || !ref.current) return;
    const [mx] = d3.pointer(e.nativeEvent, svgRef.current);
    const plotX = mx - MARGIN.left;
    if (plotX < 0 || plotX > innerW) { setTooltip(null); return; }

    const targetDate = xScale.invert(plotX);
    const entries = series
      .filter((s) => s.points.length > 0)
      .map((s) => {
        const idx = Math.max(0, Math.min(s.points.length - 1, bisect(s.points, targetDate)));
        const pt = s.points[idx]!;
        const prevPt = idx > 0 ? s.points[idx - 1] : null;
        return {
          id: s.id,
          value: pt.value,
          prevValue: prevPt?.value ?? null,
          cy: yScale(pt.value),
          strokeClassName: s.strokeClassName,
        };
      });

    const nearestDate = new Date(
      entries.length
        ? series[0]!.points[
            Math.max(0, Math.min(series[0]!.points.length - 1, bisect(series[0]!.points, targetDate)))
          ]!.ts
        : targetDate,
    );

    const containerRect = ref.current.getBoundingClientRect();
    const svgRect = svgRef.current.getBoundingClientRect();
    const tooltipX = svgRect.left - containerRect.left + mx;
    const tooltipY = svgRect.top - containerRect.top + MARGIN.top + Math.min(...entries.map((e) => e.cy));

    setTooltip({ x: tooltipX, y: tooltipY, date: nearestDate, entries });
  }

  return (
    <div ref={ref} className={cn("relative w-full", className)}>
      <svg ref={svgRef} width={width} height={height} role="img" aria-label={ariaLabel}>
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {/* Horizontal gridlines */}
          {yScale.ticks(yTicks).map((t) => (
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

          {/* Y axis labels */}
          {yScale.ticks(yTicks).map((t) => (
            <text
              key={`yt-${t}`}
              x={-6}
              y={yScale(t)}
              dy="0.32em"
              textAnchor="end"
              className="fill-fg-subtle font-mono text-[10px] tracking-wider"
            >
              {yFormat(t)}
            </text>
          ))}

          {/* X axis labels */}
          {xScale.ticks(xTicks).map((t) => (
            <text
              key={`xt-${t.toISOString()}`}
              x={xScale(t)}
              y={innerH + 14}
              textAnchor="middle"
              className="fill-fg-subtle font-mono text-[10px] tracking-wider"
            >
              {d3.timeFormat("%b %d")(t)}
            </text>
          ))}

          {/* Confidence bands */}
          {series.map((s) =>
            s.band && s.band.length === s.points.length ? (
              <path
                key={`band-${s.id}`}
                d={
                  d3
                    .area<{ lower: number; upper: number; ts: string | Date }>()
                    .x((d) => xScale(new Date(d.ts)))
                    .y0((d) => yScale(d.lower))
                    .y1((d) => yScale(d.upper))
                    .curve(d3.curveMonotoneX)(
                    s.points.map((p, i) => ({
                      ts: p.ts,
                      lower: s.band![i]!.lower,
                      upper: s.band![i]!.upper,
                    })),
                  ) ?? ""
                }
                className={cn("fill-current opacity-20", s.bandClassName ?? "text-accent")}
              />
            ) : null,
          )}

          {/* Lines */}
          {series.map((s) => (
            <path
              key={`line-${s.id}`}
              d={lineGen(s.points) ?? ""}
              fill="none"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              pathLength={s.dashed ? undefined : 1}
              data-animate-path={s.dashed ? undefined : ""}
              strokeDasharray={s.dashed ? "4 4" : undefined}
              className={cn("stroke-fg", s.strokeClassName)}
            />
          ))}

          {/* Hover crosshair */}
          {tooltip && (
            <g className="pointer-events-none">
              <line
                x1={tooltip.x - MARGIN.left}
                x2={tooltip.x - MARGIN.left}
                y1={0}
                y2={innerH}
                className="stroke-border-strong"
                strokeDasharray="2 3"
              />
              {tooltip.entries.map((e) => (
                <circle
                  key={`dot-${e.id}`}
                  cx={tooltip.x - MARGIN.left}
                  cy={e.cy}
                  r={3}
                  className={cn("fill-current stroke-bg-canvas", e.strokeClassName ?? "text-fg")}
                  strokeWidth={1.5}
                />
              ))}
            </g>
          )}

          {/* Interaction surface */}
          <rect
            x={0}
            y={0}
            width={innerW}
            height={innerH}
            fill="transparent"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setTooltip(null)}
          />

          {yLabel && (
            <text
              x={-MARGIN.left + 4}
              y={-4}
              className="fill-fg-subtle font-mono text-[10px] uppercase tracking-[0.14em]"
            >
              {yLabel}
            </text>
          )}
        </g>
      </svg>

      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg border border-border-subtle bg-bg-elevated/95 px-2.5 py-1.5 text-[11px] leading-tight shadow-lg backdrop-blur-md"
          style={{ left: tooltip.x, top: tooltip.y - 8 }}
        >
          <div className="font-mono uppercase tracking-[0.14em] text-fg-subtle">
            {d3.timeFormat("%b %d %Y")(tooltip.date)}
          </div>
          {tooltip.entries.map((e) => {
            const delta =
              e.prevValue != null && e.prevValue !== 0
                ? (e.value - e.prevValue) / Math.abs(e.prevValue)
                : null;
            return (
              <div key={e.id} className="flex items-center gap-2 tabular-nums text-fg">
                <span
                  className={cn("inline-block h-2 w-2 shrink-0 rounded-full bg-current", e.strokeClassName ?? "text-fg")}
                  aria-hidden
                />
                <span className="text-fg-muted">{e.id}</span>
                <span>{yFormat(e.value)}</span>
                {delta !== null && (
                  <span className={delta >= 0 ? "text-signal-pos" : "text-signal-neg"}>
                    {delta >= 0 ? "+" : ""}{(delta * 100).toFixed(2)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
