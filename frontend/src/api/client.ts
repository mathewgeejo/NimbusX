import type {
  Analysis,
  AnalysisEvidence,
  AlertEvaluationResult,
  AlertEvent,
  AlertRule,
  AssetImportRequest,
  AssetImportResult,
  AssetTemplate,
  CompareRequest,
  CompareResponse,
  CreateAnalysisRequest,
  CreateAnalysisResponse,
  CreateAlertRuleRequest,
  CreateNotificationChannelRequest,
  CreatePortfolioAssetRequest,
  CreateProjectRequest,
  CreateSiteRequest,
  EvaluateAlertRuleRequest,
  EvidenceRecord,
  NotificationChannel,
  NotificationDispatchReceipt,
  PortfolioAsset,
  Project,
  ReportFormat,
  Site,
  SourceHealthResponse
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
const operationalFindingStatuses = [
  "action_required",
  "monitored",
  "insufficient_context",
  "source_unavailable"
] as const;
const severities = ["low", "moderate", "high", "unknown"] as const;
const actionableSeverities = ["low", "moderate", "high"] as const;
const calibrationStatuses = [
  "not_applicable",
  "unavailable",
  "calibrated",
  "insufficient_skill"
] as const;
const decisions = ["acceptable", "mitigation_required", "high_risk", "insufficient_evidence"] as const;
const assetCriticalities = ["low", "medium", "high", "critical"] as const;
const alertTriggerTypes = [
  "observed_threshold_breach",
  "baseline_likelihood",
  "severity_at_least"
] as const;
const alertDeliveryStatuses = ["recorded_only"] as const;
const alertEventKinds = ["observed_threshold_breach", "historical_pattern", "severity_trigger"] as const;
const notificationChannelKinds = ["webhook", "email", "slack"] as const;
const notificationDeliveryModes = ["dry_run", "live"] as const;
const notificationReceiptStatuses = ["dry_run", "unavailable", "disabled"] as const;
const assetImportStatuses = ["complete", "partial", "failed"] as const;
const assetImportRowStatuses = ["created", "validated", "rejected"] as const;
const sourceCapabilities = [
  "observed_daily",
  "historical_baseline",
  "operational_forecast",
  "seasonal_outlook",
  "scenario_projection",
  "flood_exposure",
  "wildfire_exposure",
  "water_stress_exposure"
] as const;
const sourceImplementationStates = ["implemented", "unavailable"] as const;
const sourceHealthStatuses = ["not_checked", "unavailable", "degraded"] as const;
const remoteProbePolicies = ["on_retrieval", "explicit_only", "not_applicable"] as const;

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

function nullableNumberField(record: UnknownRecord, field: string, resource: string): number | null {
  const value = record[field];
  if (value !== null && (typeof value !== "number" || !Number.isFinite(value))) {
    throw invalidResponse(resource);
  }
  return value;
}

function objectRecordField(record: UnknownRecord, field: string, resource: string): UnknownRecord {
  return recordOf(record[field], resource);
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

function validateOperationalFinding(value: unknown, resource: string): void {
  const finding = recordOf(value, resource);
  stringField(finding, "asset_id", resource);
  stringField(finding, "template_id", resource);
  stringField(finding, "rule_id", resource);
  stringField(finding, "rule_name", resource);
  literalField(finding, "hazard", hazardTypes, resource);
  literalField(finding, "status", operationalFindingStatuses, resource);
  literalField(finding, "source_finding_status", findingStatuses, resource);
  literalField(finding, "source_severity", severities, resource);
  stringArrayField(finding, "evidence_ids", resource);
  nullableStringField(finding, "action", resource);
  stringField(finding, "rationale", resource);
  stringArrayField(finding, "missing_exposure_fields", resource);
  stringArrayField(finding, "missing_vulnerability_fields", resource);
}

function validateAnalysis(value: unknown): Analysis {
  const resource = "analysis";
  const analysis = recordOf(value, resource);
  stringField(analysis, "id", resource);
  literalField(analysis, "status", analysisStatuses, resource);
  literalField(analysis, "mode", analysisModes, resource);
  nullableStringField(analysis, "project_id", resource);
  nullableStringField(analysis, "asset_id", resource);
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
  arrayField(analysis, "operational_findings", resource).forEach((finding) =>
    validateOperationalFinding(finding, resource)
  );

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

function validateAssetTemplateField(value: unknown, resource: string): void {
  const field = recordOf(value, resource);
  stringField(field, "key", resource);
  stringField(field, "label", resource);
  stringField(field, "description", resource);
  literalField(field, "value_type", ["string", "number", "boolean", "enum"] as const, resource);
  stringArrayField(field, "allowed_values", resource);
  if (typeof field.required !== "boolean") {
    throw invalidResponse(resource);
  }
}

function validateAssetTemplate(value: unknown): AssetTemplate {
  const resource = "asset template";
  const template = recordOf(value, resource);
  stringField(template, "id", resource);
  stringField(template, "display_name", resource);
  stringField(template, "description", resource);
  arrayField(template, "required_exposure_fields", resource).forEach((field) =>
    validateAssetTemplateField(field, resource)
  );
  arrayField(template, "required_vulnerability_fields", resource).forEach((field) =>
    validateAssetTemplateField(field, resource)
  );
  arrayField(template, "supported_hazards", resource).forEach((hazard) => {
    if (typeof hazard !== "string" || !hazardTypes.includes(hazard as (typeof hazardTypes)[number])) {
      throw invalidResponse(resource);
    }
  });
  arrayField(template, "operational_rules", resource).forEach((value) => {
    const rule = recordOf(value, resource);
    stringField(rule, "id", resource);
    stringField(rule, "name", resource);
    literalField(rule, "hazard", hazardTypes, resource);
    literalField(rule, "minimum_severity", actionableSeverities, resource);
    stringArrayField(rule, "required_exposure_fields", resource);
    stringArrayField(rule, "required_vulnerability_fields", resource);
    stringField(rule, "action", resource);
    stringField(rule, "rationale", resource);
  });
  stringField(template, "version", resource);
  return template as unknown as AssetTemplate;
}

function validatePortfolioAsset(value: unknown): PortfolioAsset {
  const resource = "portfolio asset";
  const asset = recordOf(value, resource);
  stringField(asset, "id", resource);
  stringField(asset, "project_id", resource);
  stringField(asset, "site_id", resource);
  stringField(asset, "template_id", resource);
  stringField(asset, "name", resource);
  nullableStringField(asset, "external_id", resource);
  literalField(asset, "criticality", assetCriticalities, resource);
  stringArrayField(asset, "tags", resource);
  objectRecordField(asset, "exposure", resource);
  objectRecordField(asset, "vulnerability", resource);
  stringField(asset, "created_at", resource);
  return asset as unknown as PortfolioAsset;
}

function validateAssetImportResult(value: unknown): AssetImportResult {
  const resource = "asset import";
  const result = recordOf(value, resource);
  stringField(result, "project_id", resource);
  if (typeof result.dry_run !== "boolean") {
    throw invalidResponse(resource);
  }
  literalField(result, "status", assetImportStatuses, resource);
  numberField(result, "created_count", resource);
  numberField(result, "rejected_count", resource);
  arrayField(result, "rows", resource).forEach((value) => {
    const row = recordOf(value, resource);
    numberField(row, "row_number", resource);
    nullableStringField(row, "name", resource);
    literalField(row, "status", assetImportRowStatuses, resource);
    nullableStringField(row, "asset_id", resource);
    nullableStringField(row, "site_id", resource);
    nullableStringField(row, "code", resource);
    stringField(row, "message", resource);
  });
  stringArrayField(result, "limitations", resource);
  return result as unknown as AssetImportResult;
}

function validateAlertRule(value: unknown): AlertRule {
  const resource = "alert rule";
  const rule = recordOf(value, resource);
  stringField(rule, "id", resource);
  stringField(rule, "project_id", resource);
  stringField(rule, "name", resource);
  nullableStringField(rule, "asset_id", resource);
  literalField(rule, "hazard", hazardTypes, resource);
  literalField(rule, "trigger_type", alertTriggerTypes, resource);
  nullableNumberField(rule, "minimum_likelihood", resource);
  nullableLiteralField(rule, "minimum_severity", actionableSeverities, resource);
  if (typeof rule.enabled !== "boolean") {
    throw invalidResponse(resource);
  }
  stringField(rule, "created_at", resource);
  return rule as unknown as AlertRule;
}

function validateAlertEvent(value: unknown): AlertEvent {
  const resource = "alert event";
  const event = recordOf(value, resource);
  stringField(event, "id", resource);
  stringField(event, "project_id", resource);
  stringField(event, "rule_id", resource);
  nullableStringField(event, "asset_id", resource);
  stringField(event, "analysis_id", resource);
  literalField(event, "hazard", hazardTypes, resource);
  literalField(event, "event_kind", alertEventKinds, resource);
  stringField(event, "summary", resource);
  stringArrayField(event, "evidence_ids", resource);
  literalField(event, "delivery_status", alertDeliveryStatuses, resource);
  stringField(event, "created_at", resource);
  return event as unknown as AlertEvent;
}

function validateNotificationChannel(value: unknown): NotificationChannel {
  const resource = "notification channel";
  const channel = recordOf(value, resource);
  stringField(channel, "id", resource);
  stringField(channel, "project_id", resource);
  stringField(channel, "name", resource);
  literalField(channel, "kind", notificationChannelKinds, resource);
  stringField(channel, "target", resource);
  if (typeof channel.enabled !== "boolean" || typeof channel.has_secret_reference !== "boolean") {
    throw invalidResponse(resource);
  }
  literalField(channel, "delivery_mode", notificationDeliveryModes, resource);
  stringField(channel, "created_at", resource);
  return channel as unknown as NotificationChannel;
}

function validateNotificationDispatchReceipt(value: unknown): NotificationDispatchReceipt {
  const resource = "notification dispatch receipt";
  const receipt = recordOf(value, resource);
  stringField(receipt, "id", resource);
  stringField(receipt, "project_id", resource);
  stringField(receipt, "alert_event_id", resource);
  stringField(receipt, "channel_id", resource);
  literalField(receipt, "status", notificationReceiptStatuses, resource);
  stringField(receipt, "created_at", resource);
  stringField(receipt, "message", resource);
  objectRecordField(receipt, "payload", resource);
  return receipt as unknown as NotificationDispatchReceipt;
}

function validateAlertEvaluationResult(value: unknown): AlertEvaluationResult {
  const resource = "alert evaluation";
  const result = recordOf(value, resource);
  validateAlertRule(result.rule);
  arrayField(result, "events", resource).forEach((event) => validateAlertEvent(event));
  numberField(result, "created_count", resource);
  numberField(result, "existing_count", resource);
  arrayField(result, "skipped", resource).forEach((value) => {
    const skipped = recordOf(value, resource);
    stringField(skipped, "analysis_id", resource);
    stringField(skipped, "reason", resource);
  });
  stringArrayField(result, "limitations", resource);
  return result as unknown as AlertEvaluationResult;
}

function validateSourceHealthResponse(value: unknown): SourceHealthResponse {
  const resource = "source health";
  const response = recordOf(value, resource);
  stringField(response, "generated_at", resource);
  arrayField(response, "sources", resource).forEach((value) => {
    const source = recordOf(value, resource);
    stringField(source, "id", resource);
    stringField(source, "provider", resource);
    stringField(source, "dataset", resource);
    arrayField(source, "capabilities", resource).forEach((capability) => {
      if (
        typeof capability !== "string" ||
        !sourceCapabilities.includes(capability as (typeof sourceCapabilities)[number])
      ) {
        throw invalidResponse(resource);
      }
    });
    literalField(source, "implementation", sourceImplementationStates, resource);
    literalField(source, "remote_probe_policy", remoteProbePolicies, resource);
    const evidenceContract = objectRecordField(source, "evidence_contract", resource);
    if (
      typeof evidenceContract.requires_model_version !== "boolean" ||
      typeof evidenceContract.requires_raw_extract !== "boolean"
    ) {
      throw invalidResponse(resource);
    }
    stringArrayField(evidenceContract, "required_query_keys", resource);
    stringArrayField(evidenceContract, "required_unit_keys", resource);
    stringArrayField(source, "limitations", resource);
    literalField(source, "status", sourceHealthStatuses, resource);
    stringField(source, "checked_at", resource);
    if (typeof source.remote_checked !== "boolean") {
      throw invalidResponse(resource);
    }
    stringField(source, "message", resource);
    const details = objectRecordField(source, "details", resource);
    if (
      !Object.values(details).every(
        (detail) =>
          detail === null ||
          typeof detail === "string" ||
          typeof detail === "number" ||
          typeof detail === "boolean"
      )
    ) {
      throw invalidResponse(resource);
    }
  });
  stringArrayField(response, "limitations", resource);
  return response as unknown as SourceHealthResponse;
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

  listAssetTemplates(signal?: AbortSignal): Promise<AssetTemplate[]> {
    return request("/v1/asset-templates", { signal }, (payload) => {
      if (!Array.isArray(payload)) {
        throw invalidResponse("asset template list");
      }
      return payload.map(validateAssetTemplate);
    });
  },

  getSourceHealth(signal?: AbortSignal): Promise<SourceHealthResponse> {
    return request("/v1/sources/health", { signal }, validateSourceHealthResponse);
  },

  listProjectAssets(projectId: string, signal?: AbortSignal): Promise<PortfolioAsset[]> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/assets",
      { signal },
      (payload) => {
        if (!Array.isArray(payload)) {
          throw invalidResponse("project asset list");
        }
        return payload.map(validatePortfolioAsset);
      }
    );
  },

  createProjectAsset(projectId: string, payload: CreatePortfolioAssetRequest): Promise<PortfolioAsset> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/assets",
      { method: "POST", body: payload },
      validatePortfolioAsset
    );
  },

  importProjectAssets(projectId: string, payload: AssetImportRequest): Promise<AssetImportResult> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/assets/import",
      { method: "POST", body: payload },
      validateAssetImportResult
    );
  },

  listAlertRules(projectId: string, signal?: AbortSignal): Promise<AlertRule[]> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/alert-rules",
      { signal },
      (payload) => {
        if (!Array.isArray(payload)) {
          throw invalidResponse("alert rule list");
        }
        return payload.map(validateAlertRule);
      }
    );
  },

  createAlertRule(projectId: string, payload: CreateAlertRuleRequest): Promise<AlertRule> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/alert-rules",
      { method: "POST", body: payload },
      validateAlertRule
    );
  },

  listAlertEvents(projectId: string, signal?: AbortSignal): Promise<AlertEvent[]> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/alert-events",
      { signal },
      (payload) => {
        if (!Array.isArray(payload)) {
          throw invalidResponse("alert event list");
        }
        return payload.map(validateAlertEvent);
      }
    );
  },

  listNotificationChannels(projectId: string, signal?: AbortSignal): Promise<NotificationChannel[]> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/notification-channels",
      { signal },
      (payload) => {
        if (!Array.isArray(payload)) {
          throw invalidResponse("notification channel list");
        }
        return payload.map(validateNotificationChannel);
      }
    );
  },

  createNotificationChannel(
    projectId: string,
    payload: CreateNotificationChannelRequest
  ): Promise<NotificationChannel> {
    return request(
      "/v1/projects/" + encodeURIComponent(projectId) + "/notification-channels",
      { method: "POST", body: payload },
      validateNotificationChannel
    );
  },

  listNotificationReceipts(
    projectId: string,
    eventId: string,
    signal?: AbortSignal
  ): Promise<NotificationDispatchReceipt[]> {
    return request(
      "/v1/projects/" +
        encodeURIComponent(projectId) +
        "/alert-events/" +
        encodeURIComponent(eventId) +
        "/notification-receipts",
      { signal },
      (payload) => {
        if (!Array.isArray(payload)) {
          throw invalidResponse("notification receipt list");
        }
        return payload.map(validateNotificationDispatchReceipt);
      }
    );
  },

  dispatchAlertEvent(
    projectId: string,
    eventId: string,
    channelId: string
  ): Promise<NotificationDispatchReceipt> {
    return request(
      "/v1/projects/" +
        encodeURIComponent(projectId) +
        "/alert-events/" +
        encodeURIComponent(eventId) +
        "/notification-channels/" +
        encodeURIComponent(channelId) +
        "/dispatch",
      { method: "POST" },
      validateNotificationDispatchReceipt
    );
  },

  evaluateAlertRule(
    projectId: string,
    ruleId: string,
    payload: EvaluateAlertRuleRequest
  ): Promise<AlertEvaluationResult> {
    return request(
      "/v1/projects/" +
        encodeURIComponent(projectId) +
        "/alert-rules/" +
        encodeURIComponent(ruleId) +
        "/evaluate",
      { method: "POST", body: payload },
      validateAlertEvaluationResult
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
