"use client";

import * as React from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Production-capable table primitive, restyled for the Apple Pro system.
 *
 * - Controlled sorting: callers pass `sortKey`/`sortDir` and a handler.
 * - Sticky header with frosted backdrop so long lists stay legible.
 * - Row `onClick` surfaces selection to parent state; active rows tint
 *   with the accent colour.
 * - Every cell can opt into numeric alignment via `align: "right"`.
 */

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  accessor: (row: T) => React.ReactNode;
  sortValue?: (row: T) => number | string | null;
  width?: string;
  align?: "left" | "right" | "center";
  className?: string;
  headerClassName?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  activeRowKey?: string | null;
  sortKey?: string | null;
  sortDir?: "asc" | "desc" | null;
  onSort?: (key: string) => void;
  emptyState?: React.ReactNode;
  className?: string;
  maxHeight?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  activeRowKey,
  sortKey,
  sortDir,
  onSort,
  emptyState,
  className,
  maxHeight = "calc(100vh - 320px)",
}: DataTableProps<T>) {
  return (
    <div
      className={cn(
        "overflow-auto rounded-2xl border border-border-subtle bg-bg-panel/60 backdrop-blur-sm",
        className,
      )}
      style={{ maxHeight }}
    >
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 z-10 bg-bg-inset/80 backdrop-blur-md">
          <tr>
            {columns.map((col) => {
              const isSorted = sortKey === col.key;
              const SortIcon =
                isSorted && sortDir === "asc"
                  ? ArrowUp
                  : isSorted && sortDir === "desc"
                    ? ArrowDown
                    : ArrowUpDown;
              return (
                <th
                  key={col.key}
                  scope="col"
                  style={{ width: col.width }}
                  className={cn(
                    "border-b border-border-subtle px-4 py-3 text-[10px] font-medium uppercase tracking-[0.14em] text-fg-subtle",
                    col.align === "right" && "text-right",
                    col.align === "center" && "text-center",
                    col.headerClassName,
                  )}
                >
                  {col.sortValue && onSort ? (
                    <button
                      type="button"
                      onClick={() => onSort(col.key)}
                      className={cn(
                        "inline-flex items-center gap-1.5 transition-colors hover:text-fg",
                        col.align === "right" && "ml-auto",
                      )}
                    >
                      <span>{col.header}</span>
                      <SortIcon
                        className={cn(
                          "h-3 w-3 opacity-50",
                          isSorted && "text-accent opacity-100",
                        )}
                      />
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-10 text-center text-xs text-fg-muted"
              >
                {emptyState ?? "No rows"}
              </td>
            </tr>
          ) : (
            rows.map((row) => {
              const key = rowKey(row);
              const isActive = key === activeRowKey;
              return (
                <tr
                  key={key}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(
                    "border-b border-border-subtle/70 transition-colors",
                    onRowClick && "cursor-pointer hover:bg-bg-raised/70",
                    isActive && "bg-accent/10 hover:bg-accent/15",
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        "px-4 py-3 text-fg",
                        col.align === "right" && "text-right tabular-nums",
                        col.align === "center" && "text-center",
                        col.className,
                      )}
                    >
                      {col.accessor(row)}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
