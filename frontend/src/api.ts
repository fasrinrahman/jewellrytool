import type { BuildResponse, CheckResult, RingParams, Rules, SizeSystem, Sizes } from "./types";

const BASE: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  report?: { exportable: boolean; results: CheckResult[] };
  constructor(message: string, status: number, report?: ApiError["report"]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.report = report;
  }
}

const FIELD_LABELS: Record<string, string> = {
  ring_size_mm: "Ring size", band_width_mm: "Band width", band_thickness_mm: "Band thickness",
  stone_size_mm: "Stone size", prong_count: "Prong count", prong_diameter_mm: "Prong thickness", metal: "Metal",
};

/** The server reports where a value is wrong (never the value itself); say it in plain words. */
function fieldMessage(first: unknown): string {
  const e = first as { loc?: string[]; msg?: string } | undefined;
  const field = e?.loc?.[e.loc.length - 1] ?? "";
  const label = FIELD_LABELS[field];
  return label ? `${label} is not a valid value. ${e?.msg ?? ""}`.trim() : "Some values are not valid.";
}

async function toApiError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* not JSON */
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return new ApiError(detail, res.status);
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const d = detail as { message?: string; report?: ApiError["report"] };
    return new ApiError(d.message ?? "The server refused the request.", res.status, d.report);
  }
  if (Array.isArray(detail)) return new ApiError(fieldMessage(detail[0]), res.status);
  return new ApiError(`The server returned an error (${res.status}).`, res.status);
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("Could not reach the design server. Is it running?", 0);
  }
  if (!res.ok) throw await toApiError(res);
  return res;
}

const post = (path: string, body: unknown): Promise<Response> =>
  request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export async function buildDesign(params: RingParams): Promise<BuildResponse> {
  return (await post("/designs/build", params)).json();
}

export async function exportDesign(params: RingParams): Promise<Blob> {
  return (await post("/designs/export", params)).blob();
}

export async function fetchRules(): Promise<Rules> {
  return (await request("/rules")).json();
}

export async function fetchSizes(system: SizeSystem, value: string): Promise<Sizes> {
  const q = new URLSearchParams({ system, value });
  return (await request(`/sizes?${q}`)).json();
}
