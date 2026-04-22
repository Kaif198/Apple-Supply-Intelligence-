"use client";

import * as React from "react";
import {
  select,
  zoom,
  drag,
  forceSimulation,
  forceManyBody,
  forceLink,
  forceCenter,
  forceRadial,
  forceCollide,
} from "d3";
import type { SimulationNodeDatum, SimulationLinkDatum } from "d3";
import { cn } from "@/lib/utils";

export interface NetworkNode {
  id: string;
  name: string;
  tier: number;
  country?: string | null;
  severity?: "low" | "medium" | "high" | "critical";
  size?: number;
  kind?: "apple" | "supplier" | "region";
  spend?: number;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight?: number;
}

interface NetworkGraphProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  height?: number;
  onSelect?: (node: NetworkNode | null) => void;
  className?: string;
  ariaLabel?: string;
}

const SEVERITY_FILL: Record<NonNullable<NetworkNode["severity"]>, string> = {
  low:      "hsl(var(--severity-low))",
  medium:   "hsl(var(--severity-medium))",
  high:     "hsl(var(--severity-high))",
  critical: "hsl(var(--severity-critical))",
};

const SEVERITY_PILL: Record<NonNullable<NetworkNode["severity"]>, string> = {
  low:      "bg-severity-low/20 text-severity-low",
  medium:   "bg-severity-medium/20 text-severity-medium",
  high:     "bg-severity-high/20 text-severity-high",
  critical: "bg-severity-critical/20 text-severity-critical",
};

type SimNode = NetworkNode & SimulationNodeDatum;
type SimLink = NetworkEdge & SimulationLinkDatum<SimNode>;

interface HoverNode {
  data: NetworkNode;
  x: number;
  y: number;
}

export function NetworkGraph({
  nodes,
  edges,
  height = 560,
  onSelect,
  className,
  ariaLabel = "Supplier network graph",
}: NetworkGraphProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const svgRef = React.useRef<SVGSVGElement | null>(null);
  const [width, setWidth] = React.useState(800);
  const [active, setActive] = React.useState<string | null>(null);
  const [hover, setHover] = React.useState<HoverNode | null>(null);

  React.useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const ro = new ResizeObserver(([entry]) => {
      if (entry) setWidth(Math.max(320, entry.contentRect.width));
    });
    ro.observe(node);
    return () => ro.disconnect();
  }, []);

  React.useEffect(() => {
    if (!svgRef.current) return;
    const svg = select(svgRef.current);
    svg.selectAll("*").remove();

    const simNodes = nodes.map((n) => ({ ...n })) as SimNode[];
    const simLinks = edges.map((e) => ({ ...e })) as SimLink[];

    const g = svg.attr("viewBox", `0 0 ${width} ${height}`).append("g");

    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.35, 3])
      .on("zoom", (event) => g.attr("transform", event.transform));
    svg.call(zoomBehavior);

    const simulation = forceSimulation<SimNode>(simNodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance((d) => 55 + 35 * (1 / Math.max(d.weight ?? 1, 0.1)))
          .strength(0.35),
      )
      .force("charge", forceManyBody().strength(-160))
      .force("center", forceCenter(width / 2, height / 2))
      .force(
        "radial",
        forceRadial<SimNode>(
          (d) => 60 + d.tier * 90,
          width / 2,
          height / 2,
        ).strength(0.18),
      )
      .force("collide", forceCollide<SimNode>().radius((d) => (d.size ?? 6) + 4))
      .alpha(1)
      .alphaDecay(0.035);

    const link = g
      .append("g")
      .attr("stroke-linecap", "round")
      .selectAll<SVGLineElement, SimLink>("line")
      .data(simLinks)
      .join("line")
      .attr("stroke", "hsl(var(--border-strong))")
      .attr("stroke-opacity", 0.4)
      .attr("stroke-width", (d) => 0.5 + Math.min(2, Math.log2(1 + (d.weight ?? 1))));

    const node = g
      .append("g")
      .selectAll<SVGCircleElement, SimNode>("circle")
      .data(simNodes)
      .join("circle")
      .attr("r", (d) => d.size ?? (d.kind === "apple" ? 14 : 7))
      .attr("fill", (d) =>
        d.kind === "apple"
          ? "hsl(var(--accent))"
          : d.severity
            ? SEVERITY_FILL[d.severity]
            : "hsl(var(--fg-subtle))",
      )
      .attr("stroke", (d) => (d.id === active ? "hsl(var(--accent-muted))" : "hsl(var(--bg-canvas))"))
      .attr("stroke-width", (d) => (d.id === active ? 2.5 : 1.5))
      .attr("cursor", "pointer")
      .on("click", (_, d) => {
        const next = d.id === active ? null : d.id;
        setActive(next);
        onSelect?.(next ? d : null);
      })
      .on("mouseover", (event: MouseEvent, d) => {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        setHover({ data: d, x: event.clientX - rect.left, y: event.clientY - rect.top });
      })
      .on("mousemove", (event: MouseEvent) => {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        setHover((prev) => prev ? { ...prev, x: event.clientX - rect.left, y: event.clientY - rect.top } : prev);
      })
      .on("mouseout", () => setHover(null))
      .call(
        drag<SVGCircleElement, SimNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }),
      );

    const label = g
      .append("g")
      .selectAll<SVGTextElement, SimNode>("text")
      .data(simNodes.filter((d) => (d.size ?? 0) >= 10 || d.kind === "apple"))
      .join("text")
      .text((d) => d.name)
      .attr("font-family", "var(--font-mono)")
      .attr("font-size", 10)
      .attr("letter-spacing", "0.04em")
      .attr("fill", "hsl(var(--fg-subtle))")
      .attr("text-anchor", "middle")
      .attr("pointer-events", "none");

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as SimNode).x ?? 0)
        .attr("y1", (d) => (d.source as SimNode).y ?? 0)
        .attr("x2", (d) => (d.target as SimNode).x ?? 0)
        .attr("y2", (d) => (d.target as SimNode).y ?? 0);
      node.attr("cx", (d) => d.x ?? 0).attr("cy", (d) => d.y ?? 0);
      label.attr("x", (d) => d.x ?? 0).attr("y", (d) => (d.y ?? 0) - (d.size ?? 7) - 5);
    });

    return () => { simulation.stop(); };
  }, [nodes, edges, width, height, active, onSelect]);

  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        role="img"
        aria-label={ariaLabel}
        className="cursor-grab active:cursor-grabbing"
      />

      {hover && hover.data.kind !== "apple" && (
        <div
          className="pointer-events-none absolute z-20 min-w-[140px] rounded-lg border border-border-subtle bg-bg-elevated/95 px-3 py-2 text-[11px] leading-snug shadow-lg backdrop-blur-md"
          style={{ left: hover.x + 14, top: hover.y - 10 }}
        >
          <div className="font-semibold text-fg">{hover.data.name}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-fg-muted">
            <span>Tier {hover.data.tier}</span>
            {hover.data.country && (
              <>
                <span className="opacity-40">·</span>
                <span>{hover.data.country}</span>
              </>
            )}
          </div>
          {hover.data.spend != null && (
            <div className="mt-1 tabular-nums text-fg-muted">
              Spend · ${hover.data.spend.toFixed(2)}B
            </div>
          )}
          {hover.data.severity && (
            <div
              className={cn(
                "mt-1.5 inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider",
                SEVERITY_PILL[hover.data.severity],
              )}
            >
              {hover.data.severity}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
