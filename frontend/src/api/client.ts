import type {
  Analysis,
  AnalysisEvidence,
  CompareRequest,
  CompareResponse,
  CreateAnalysisRequest,
  CreateAnalysisResponse,
  CreateProjectRequest,
  CreateSiteRequest,
  EvidenceRecord,
  Project,
  ReportFormat,
  Site
} from "./contracts";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;
  readonly requestId?: string;

  constructor(
    message: string,
    options: {
      code?: string;
      status: number;
      details?: unknown;
      requestId?: string;
    }
  ) {
    super(message);
    this.name = "ApiError";
    this.code = options.code ?? "request_failed";
    this.status = options.status;
    this.details = options.details;
    this.requestId = options.requestId;
  }
}

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_BASE_URL = configuredBaseUrl.trim().replace(/\/+$/, "");

const analysisModes = ["auto", "observed", "forecast", "seasonal", "baseline", "scenario"] as const;
const analysisStatuses = ["queued", "running", "complete", "partial", "failed", "expired"] as const;
const comparisonKinds = ["selected_assessments"] as const;
const hazardTypes = ["extreme_heat", "extreme_cold", "heavy_precipitation", "wind", "drought"] as const;
const findingStatuses = ["available", "unavailable"] as const;
const severities = ["low", "moderate", "high", "unknown"] as const;
const calibrationStatuses = [
  "not_applicable",
  "unavailable",
  "calibrated",
  "insufficient_skill"
] as const;
const decisions = ["acceptable", "mitigation_required", "high_risk", "insufficient_evidence"] as const;

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

type Decoder<T> = (payload: unknown) => T;
type UnknownRecord = Record<string, unknown>;

function endpoint(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : "/" + path;
  if (API_BASE_URL.endsWith("/v1") && normalizedPath.startsWith("/v1/")) {
    return API_BASE_URL + normalizedPath.slice(3);
  }
  return API_BASE_URL + normalizedPath;
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isAbortError(error: unknown): boolean {
  return isRecord(error) && error.name === "AbortError";
}

function invalidResponse(resource: string, status = 200): ApiError {
  return new ApiError(
    "NimbusX returned an invalid " + resource + " response. No result has been displayed.",
    { code: "invalid_response", status }
  );
}

function recordOf(value: unknown, resource: string): UnknownRecord {
  if (!isRecord(value)) {
    throw invalidResponse(resource);
  }
  return value;
}

function stringField(record: UnknownRecord, field: string, resource: string): string {
  const value = record[field];
  if (typeof value !== "string") {
    throw invalidResponse(resource);
  }
  return value;
}

function numberField(record: UnknownRecord, field: string, resource: string): number {
  const value = record[field];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw invalidResponse(resource);
  }
  return value;
}

function nullableStringField(record: UnknownRecord, field: string, resource: string): string | null {
  const value = record[field];
  if (value !== null && typeof value !== "string") {
    throw invalidResponse(resource);
  }
  return value;
}

function arrayField(record: UnknownRecord, field: string, resource: string): unknown[] {
  const value = record[field];
  if (!Array.isArray(value)) {
    throw invalidResponse(resource);
  }
  return value;
}

function stringArrayField(record: UnknownRecord, field: string, resource: string): string[] {
  const value = arrayField(record, field, resource);
  if (!value.every((item) => typeof item === "string")) {
    throw invalidResponse(resource);
  }
  return value;
}

function literalField<T extends readonly string[]>(
  record: UnknownRecord,
  field: string,
  values: T,
  resource: string
): T[number] {
  const value = stringField(record, field, resource);
  if (!(values as readonly string[]).includes(value)) {
    throw invalidResponse(resource);
  }
  return value as T[number];
}

function nullableLiteralField<T extends readonly string[]>(
  record: UnknownRecord,
  field: string,
  values: T,
  resource: string
): T[number] | null {
  const value = record[field];
  if (value === null) {
    return null;
  }
  if (typeof value !== "string" || !(values as readonly string[]).includes(value)) {
    throw invalidResponse(resource);
  }
  return value as T[number];
}

function validateSiteInput(value: unknown, resource: string): void {
  const site = recordOf(value, resource);
  stringField(site, "name", resource);
  numberField(site, "latitude", resource);
  numberField(site, "longitude", resource);
  stringField(site, "timezone", resource);

  if (site.geometry !== null && site.geometry !== undefined) {
    const geometry = recordOf(site.geometry, resource);
    literalField(geometry, "type", ["Point", "Polygon"] as const, resource);
    if (!Array.isArray(geometry.coordinates)) {
      throw invalidResponse(resource);
    }
  }
  if (site.address !== null && site.address !== undefined && typeof site.address !== "string") {
    throw invalidResponse(resource);
  }
}

function validateSourceFreshness(value: unknown, resource: string): void {
  const source = recordOf(value, resource);
  stringField(source, "provider", resource);
  literalField(source, "status", ["current", "stale", "unavailable"] as const, resource);
  nullableStringField(source, "retrieved_at", resource);
  nullableStringField(source, "valid_until", resource);
  nullableStringField(source, "message", resource);
}

function validateFinding(value: unknown, resource: string): void {
  const finding = recordOf(value, resource);
  literalField(finding, "hazard", hazardTypes, resource);
  literalField(finding, "status", findingStatuses, resource);
  stringField(finding, "metric", resource);
  literalField(finding, "operator", [">=", "<=", "observed"] as const, resource);
  numberField(finding, "threshold", resource);
  stringField(finding, "unit", resource);
  stringField(finding, "event_definition", resource);
  if (finding.likelihood !== null) {
    numberField(finding, "likelihood", resource);
  }
  nullableStringField(finding, "likelihood_basis", resource);
  if (finding.observed_value !== null) {
    numberField(finding, "observed_value", resource);
  }
  if (finding.sample_size !== null) {
    numberField(finding, "sample_size", resource);
  }
  literalField(finding, "severity", severities, resource);
  literalField(finding, "calibration_status", calibrationStatuses, resource);
  nullableStringField(finding, "recommendation", resource);
  stringArrayField(finding, "evidence_ids", resource);
  nullableStringField(finding, "limitation", resource);
}

function validateAnalysis(value: unknown): Analysis {
  const resource = "analysis";
  const analysis = recordOf(value, resource);
  stringField(analysis, "id", resource);
  literalField(analysis, "status", analysisStatuses, resource);
  literalField(analysis, "mode", analysisModes, resource);
  nullableStringField(analysis, "project_id", resource);
  nullableLiteralField(analysis, "resolved_mode", analysisModes, resource);
  stringField(analysis, "created_at", resource);
  nullableStringField(analysis, "generated_at", resource);
  nullableStringField(analysis, "expires_at", resource);
  arrayField(analysis, "source_freshness", resource).forEach((source) =>
    validateSourceFreshness(source, resource)
  );
  validateSiteInput(analysis.site, resource);
  const window = recordOf(analysis.window, resource);
  stringField(window, "start", resource);
  stringField(window, "end", resource);
  arrayField(analysis, "findings", resource).forEach((finding) => validateFinding(finding, resource));

  if (analysis.decision !== null) {
    const decision = recordOf(analysis.decision, resource);
    literalField(decision, "status", decisions, resource);
    stringField(decision, "rationale", resource);
  }
  stringArrayField(analysis, "evidence_ids", resource);
  stringArrayField(analysis, "data_gaps", resource);
  stringArrayField(analysis, "limitations", resource);
  stringField(analysis, "report_version", resource);
  return analysis as unknown as Analysis;
}

function validateProject(value: unknown): Project {
  const resource = "project";
  const project = recordOf(value, resource);
  stringField(project, "id", resource);
  stringField(project, "name", resource);
  stringField(project, "organization_id", resource);
  stringField(project, "created_at", resource);
  return project as unknown as Project;
}

function validateSite(value: unknown): Site {
  const resource = "site";
  const site = recordOf(value, resource);
  validateSiteInput(site, resource);
  stringField(site, "id", resource);
  stringField(site, "project_id", resource);
  stringField(site, "created_at", resource);
  if (
    !Object.prototype.hasOwnProperty.call(site, "geometry") ||
    !Object.prototype.hasOwnProperty.call(site, "address")
  ) {
    throw invalidResponse(resource);
  }
  nullableStringField(site, "address", resource);
  return site as unknown as Site;
}

function validateEvidenceRecord(value: unknown): EvidenceRecord {
  const resource = "evidence";
  const evidence = recordOf(value, resource);
  stringField(evidence, "id", resource);
  stringField(evidence, "provider", resource);
  stringField(evidence, "dataset", resource);
  nullableStringField(evidence, "model_version", resource);
  stringField(evidence, "retrieved_at", resource);
  recordOf(evidence.query, resource);
  const units = recordOf(evidence.units, resource);
  if (!Object.values(units).every((unit) => typeof unit === "string")) {
    throw invalidResponse(resource);
  }
  stringField(evidence, "resolution", resource);
  stringField(evidence, "license", resource);
  stringField(evidence, "attribution", resource);
  stringField(evidence, "content_hash", resource);
  nullableStringField(evidence, "coverage_start", resource);
  nullableStringField(evidence, "coverage_end", resource);
  if (typeof evidence.raw_available !== "boolean") {
    throw invalidResponse(resource);
  }
  return evidence as unknown as EvidenceRecord;
}

function validateEvidence(value: unknown): AnalysisEvidence {
  const resource = "evidence";
  const evidence = recordOf(value, resource);
  stringField(evidence, "analysis_id", resource);
  arrayField(evidence, "evidence", resource).forEach((record) => validateEvidenceRecord(record));
  return evidence as unknown as AnalysisEvidence;
}

function validateCreatedAnalysis(value: unknown): CreateAnalysisResponse {
  const resource = "analysis creation";
  const analysis = recordOf(value, resource);
  stringField(analysis, "id", resource);
  literalField(analysis, "status", analysisStatuses, resource);
  literalField(analysis, "mode", analysisModes, resource);
  stringField(analysis, "created_at", resource);
  return analysis as unknown as CreateAnalysisResponse;
}

function validateComparison(value: unknown): CompareResponse {
  const resource = "comparison";
  const comparison = recordOf(value, resource);
  literalField(comparison, "comparison", comparisonKinds, resource);
  arrayField(comparison, "analyses", resource).forEach((item) => {
    const analysis = recordOf(item, resource);
    stringField(analysis, "analysis_id", resource);
    stringField(analysis, "site_name", resource);
    literalField(analysis, "status", analysisStatuses, resource);
    nullableLiteralField(analysis, "mode", analysisModes, resource);
    nullableLiteralField(analysis, "decision", decisions, resource);
    arrayField(analysis, "findings", resource).forEach((finding) => validateFinding(finding, resource));
  });
  stringArrayField(comparison, "limitations", resource);
  return comparison as unknown as CompareResponse;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      throw invalidResponse("JSON", response.status);
    }
  }

  const text = await response.text();
  return text || undefined;
}

function messageFromBody(body: unknown, fallback: string): {
  message: string;
  code?: string;
  details?: unknown;
  requestId?: string;
} {
  if (!body || typeof body !== "object") {
    return { message: typeof body === "string" ? body : fallback };
  }

  const envelope = body as {
    error?: {
      code?: string;
      message?: string;
      details?: unknown;
      request_id?: string;
    };
  };

  if (envelope.error) {
    return {
      message: envelope.error.message ?? fallback,
      code: envelope.error.code,
      details: envelope.error.details,
      requestId: envelope.error.request_id
    };
  }

  return { message: fallback };
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
  decode: Decoder<T>
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(endpoint(path), {
      ...options,
      body,
      headers,
      credentials: "same-origin"
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    throw new ApiError(
      "NimbusX could not reach the control-plane API. Check the service URL and network connection.",
      { code: "network_error", status: 0 }
    );
  }

  const parsedBody = await parseResponseBody(response);
  if (!response.ok) {
    const error = messageFromBody(parsedBody, "The request could not be completed.");
    throw new ApiError(error.message, {
      code: error.code,
      status: response.status,
      details: error.details,
      requestId: error.requestId ?? response.headers.get("x-request-id") ?? undefined
    });
  }

  return decode(parsedBody);
}

export const api = {
  listProjects(signal?: AbortSignal): Promise<Project[]> {
    return request("/v1/projects", { signal }, (payload) => {
      if (!Array.isArray(payload)) {
        throw invalidResponse("project list");
      }
      return payload.map(validateProject);
    });
  },

  createProject(payload: CreateProjectRequest): Promise<Project> {
    return request("/v1/projects", { method: "POST", body: payload }, validateProject);
  },

  createSite(projectId: string, payload: CreateSiteRequest): Promise<Site> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/sites",
      { method: "POST", body: payload },
      validateSite
    );
  },

  listProjectAnalyses(projectId: string, signal?: AbortSignal): Promise<Analysis[]> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/analyses",
      { signal },
      (payload) => {
        if (!Array.isArray(payload)) {
          throw invalidResponse("project assessment list");
        }
        return payload.map(validateAnalysis);
      }
    );
  },

  createAnalysis(payload: CreateAnalysisRequest): Promise<CreateAnalysisResponse> {
    return request("/v1/analyses", { method: "POST", body: payload }, validateCreatedAnalysis);
  },

  getAnalysis(analysisId: string, signal?: AbortSignal): Promise<Analysis> {
    return request("/v1/analyses/" + encodeURIComponent(analysisId), { signal }, validateAnalysis);
  },

  getEvidence(analysisId: string, signal?: AbortSignal): Promise<AnalysisEvidence> {
    return request(
      "/v1/analyses/" + encodeURIComponent(analysisId) + "/evidence",
      { signal },
      validateEvidence
    );
  },

  compareAnalysis(analysisId: string, payload: CompareRequest): Promise<CompareResponse> {
    return request(
      "/v1/analyses/" + encodeURIComponent(analysisId) + "/compare",
      { method: "POST", body: payload },
      validateComparison
    );
  },

  async downloadReport(analysisId: string, format: ReportFormat): Promise<Blob> {
    let response: Response;
    try {
      response = await fetch(
        endpoint("/v1/analyses/" + encodeURIComponent(analysisId) + "/report?format=" + format),
        {
          headers: { Accept: format === "csv" ? "text/csv" : "application/json" },
          credentials: "same-origin"
        }
      );
    } catch (error) {
      if (isAbortError(error)) {
        throw error;
      }
      throw new ApiError(
        "NimbusX could not reach the control-plane API. Check the service URL and network connection.",
        { code: "network_error", status: 0 }
      );
    }

    if (!response.ok) {
      const parsedBody = await parseResponseBody(response);
      const error = messageFromBody(parsedBody, "The report could not be exported.");
      throw new ApiError(error.message, {
        code: error.code,
        status: response.status,
        details: error.details,
        requestId: error.requestId ?? response.headers.get("x-request-id") ?? undefined
      });
    }

    return response.blob();
  }
};

export function evidenceById(evidence: EvidenceRecord[]): Map<string, EvidenceRecord> {
  return new Map(evidence.map((record) => [record.id, record]));
}