/**
 * Typed fetch client for the ASCIIP FastAPI backend.
 *
 * - Single base URL driven by `NEXT_PUBLIC_API_URL` (default: "/api" for
 *   Vercel rewrites to hit the Render-hosted backend via an edge proxy).
 * - Every call attaches a correlation id header so server logs and
 *   client-visible request IDs share the same token.
 * - Error responses are RFC 7807 problem+json; we parse them into a
 *   typed `ApiError`.
 */

export type Severity = "low" | "medium" | "high" | "critical";

export interface ApiProblem {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  errors?: unknown;
}

export class ApiError extends Error {
  public readonly problem: ApiProblem;
  public readonly status: number;

  constructor(problem: ApiProblem) {
    super(`${problem.status} ${problem.title}${problem.detail ? `: ${problem.detail}` : ""}`);
    this.name = "ApiError";
    this.problem = problem;
    this.status = problem.status;
  }
}

const BASE_URL = (() => {
  if (typeof window !== "undefined") {
    return (window as any).__ASCIIP_API_URL__ ?? process.env.NEXT_PUBLIC_API_URL ?? "/api";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? process.env.ASCIIP_INTERNAL_API_URL ?? "http://localhost:8000/api";
})();

function newCorrelationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return (crypto as Crypto).randomUUID();
  }
  return `cid-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal, headers = {} } = options;
  const url = `${BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const cid = newCorrelationId();

  const response = await fetch(url, {
    method,
    signal,
    credentials: "omit",
    headers: {
      Accept: "application/json, application/problem+json;q=0.9",
      "X-Correlation-Id": cid,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  const data = text ? (JSON.parse(text) as unknown) : undefined;

  if (!response.ok) {
    const problem = (data as ApiProblem | undefined) ?? {
      type: "urn:asciip:error:unknown",
      title: response.statusText || "Request failed",
      status: response.status,
    };
    throw new ApiError(problem);
  }
  return data as T;
}

/**
 * SWR fetcher — first argument is the URL path. Works with keys expressed
 * as either a bare string or a tuple `[path, params]`.
 */
export const swrFetcher = async <T>(key: string | [string, Record<string, unknown>]): Promise<T> => {
  if (typeof key === "string") {
    return apiFetch<T>(key);
  }
  const [path, params] = key;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v === undefined || v === null) continue;
    qs.set(k, String(v));
  }
  const query = qs.toString();
  return apiFetch<T>(query ? `${path}?${query}` : path);
};
