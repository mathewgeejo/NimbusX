/**
 * Mirrors the FastAPI /v1 OpenAPI contract. Values remain SI units; presentation
 * conversion belongs at the view boundary, never in the API client.
 */
export type AnalysisMode =
  | "auto"
  | "observed"
  | "forecast"
  | "seasonal"
  | "baseline"
  | "scenario";

export type AnalysisStatus =
  | "queued"
  | "running"
  | "complete"
  | "partial"
  | "failed"
  | "expired";

export type HazardType =
  | "extreme_heat"
  | "extreme_cold"
  | "heavy_precipitation"
  | "wind"
  | "drought";

export type FindingStatus = "available" | "unavailable";

export type OperationalFindingStatus =
  | "action_required"
  | "monitored"
  | "insufficient_context"
  | "source_unavailable";

export type Severity = "low" | "moderate" | "high" | "unknown";

export type CalibrationStatus =
  | "not_applicable"
  | "unavailable"
  | "calibrated"
  | "insufficient_skill";

export type Decision =
  | "acceptable"
  | "mitigation_required"
  | "high_risk"
  | "insufficient_evidence";

export type Scenario = "ssp126" | "ssp245" | "ssp585";

export type ComparisonKind = "selected_assessments";

export type ReportFormat = "json" | "csv";

export type AssetCriticality = "low" | "medium" | "high" | "critical";

export type AlertTriggerType =
  | "observed_threshold_breach"
  | "baseline_likelihood"
  | "severity_at_least";

export type AlertDeliveryStatus = "recorded_only";

export type AlertEventKind =
  | "observed_threshold_breach"
  | "historical_pattern"
  | "severity_trigger";

export type NotificationChannelKind = "webhook" | "email" | "slack";

export type NotificationDeliveryMode = "dry_run" | "live";

export type NotificationReceiptStatus = "dry_run" | "unavailable" | "disabled";

export type AssetImportStatus = "complete" | "partial" | "failed";

export type AssetImportRowStatus = "created" | "validated" | "rejected";

export type SourceCapability =
  | "observed_daily"
  | "historical_baseline"
  | "operational_forecast"
  | "seasonal_outlook"
  | "scenario_projection"
  | "flood_exposure"
  | "wildfire_exposure"
  | "water_stress_exposure";

export type SourceImplementationState = "implemented" | "unavailable";

export type SourceHealthStatus = "not_checked" | "unavailable" | "degraded";

export type RemoteProbePolicy = "on_retrieval" | "explicit_only" | "not_applicable";

export interface TimeWindow {
  start: string;
  end: string;
}

export interface GeoJsonGeometry {
  type: "Point" | "Polygon";
  coordinates: unknown[];
}

export interface SiteInput {
  name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  geometry?: GeoJsonGeometry | null;
  address?: string | null;
}

export interface AssetInput {
  template?: string;
  exposure?: Record<string, unknown>;
  vulnerability?: Record<string, unknown>;
}

export interface HazardThresholds {
  extreme_heat_c?: number;
  extreme_cold_c?: number;
  heavy_precipitation_mm?: number;
  wind_speed_m_s?: number;
  drought_precipitation_mm?: number;
}

export interface BaselinePeriod {
  start_year?: number;
  end_year?: number;
}

export interface AnalysisRequestOptions {
  project_id?: string;
  window: TimeWindow;
  mode: AnalysisMode;
  asset?: AssetInput;
  thresholds?: HazardThresholds;
  baseline?: BaselinePeriod;
  scenarios?: Scenario[];
}

export type CreateAnalysisRequest =
  | (AnalysisRequestOptions & { site: SiteInput; site_id?: never; asset_id?: never })
  | (AnalysisRequestOptions & { site_id: string; site?: never; asset_id?: never })
  | (AnalysisRequestOptions & { asset_id: string; site?: never; site_id?: never });

export interface CreateAnalysisResponse {
  id: string;
  status: AnalysisStatus;
  mode: AnalysisMode;
  created_at: string;
}

export interface SourceFreshness {
  provider: string;
  status: "current" | "stale" | "unavailable";
  retrieved_at: string | null;
  valid_until: string | null;
  message: string | null;
}

export interface HazardFinding {
  hazard: HazardType;
  status: FindingStatus;
  metric: string;
  operator: ">=" | "<=" | "observed";
  threshold: number;
  unit: string;
  event_definition: string;
  likelihood: number | null;
  likelihood_basis: string | null;
  observed_value: number | null;
  sample_size: number | null;
  severity: Severity;
  calibration_status: CalibrationStatus;
  recommendation: string | null;
  evidence_ids: string[];
  limitation: string | null;
}

export interface AnalysisDecision {
  status: Decision;
  rationale: string;
}

export interface OperationalRiskFinding {
  asset_id: string;
  template_id: string;
  rule_id: string;
  rule_name: string;
  hazard: HazardType;
  status: OperationalFindingStatus;
  source_finding_status: FindingStatus;
  source_severity: Severity;
  evidence_ids: string[];
  action: string | null;
  rationale: string;
  missing_exposure_fields: string[];
  missing_vulnerability_fields: string[];
}

export interface Analysis {
  id: string;
  status: AnalysisStatus;
  mode: AnalysisMode;
  project_id: string | null;
  asset_id: string | null;
  resolved_mode: AnalysisMode | null;
  created_at: string;
  generated_at: string | null;
  expires_at: string | null;
  source_freshness: SourceFreshness[];
  site: SiteInput;
  window: TimeWindow;
  findings: HazardFinding[];
  operational_findings: OperationalRiskFinding[];
  decision: AnalysisDecision | null;
  evidence_ids: string[];
  data_gaps: string[];
  limitations: string[];
  report_version: string;
}

export interface EvidenceRecord {
  id: string;
  provider: string;
  dataset: string;
  model_version: string | null;
  retrieved_at: string;
  query: Record<string, unknown>;
  units: Record<string, string>;
  resolution: string;
  license: string;
  attribution: string;
  content_hash: string;
  coverage_start: string | null;
  coverage_end: string | null;
  raw_available: boolean;
}

export interface AnalysisEvidence {
  analysis_id: string;
  evidence: EvidenceRecord[];
}

export interface Project {
  id: string;
  name: string;
  organization_id: string;
  created_at: string;
}

export interface CreateProjectRequest {
  name: string;
  organization_id?: string;
}

export interface Site extends Omit<SiteInput, "geometry" | "address"> {
  id: string;
  project_id: string;
  created_at: string;
  geometry: GeoJsonGeometry | null;
  address: string | null;
}

export interface AssetTemplateField {
  key: string;
  label: string;
  description: string;
  value_type: "string" | "number" | "boolean" | "enum";
  allowed_values: string[];
  required: boolean;
}

export interface AssetTemplate {
  id: string;
  display_name: string;
  description: string;
  required_exposure_fields: AssetTemplateField[];
  required_vulnerability_fields: AssetTemplateField[];
  supported_hazards: HazardType[];
  operational_rules: TemplateOperationalRule[];
  version: string;
}

export interface TemplateOperationalRule {
  id: string;
  name: string;
  hazard: HazardType;
  minimum_severity: Exclude<Severity, "unknown">;
  required_exposure_fields: string[];
  required_vulnerability_fields: string[];
  action: string;
  rationale: string;
}

export interface PortfolioAsset {
  id: string;
  project_id: string;
  site_id: string;
  template_id: string;
  name: string;
  external_id: string | null;
  criticality: AssetCriticality;
  tags: string[];
  exposure: Record<string, unknown>;
  vulnerability: Record<string, unknown>;
  created_at: string;
}

export interface CreatePortfolioAssetRequest {
  name: string;
  site_id: string;
  template_id: string;
  external_id?: string | null;
  criticality?: AssetCriticality;
  tags?: string[];
  exposure?: Record<string, unknown>;
  vulnerability?: Record<string, unknown>;
}

export interface GeoJsonFeatureCollection {
  type: "FeatureCollection";
  features: unknown[];
}

export interface AssetImportRequest {
  csv_text?: string;
  geojson?: GeoJsonFeatureCollection;
  default_template_id?: string;
  dry_run?: boolean;
}

export interface AssetImportRow {
  row_number: number;
  name: string | null;
  status: AssetImportRowStatus;
  asset_id: string | null;
  site_id: string | null;
  code: string | null;
  message: string;
}

export interface AssetImportResult {
  project_id: string;
  dry_run: boolean;
  status: AssetImportStatus;
  created_count: number;
  rejected_count: number;
  rows: AssetImportRow[];
  limitations: string[];
}

export interface AlertRule {
  id: string;
  project_id: string;
  name: string;
  asset_id: string | null;
  hazard: HazardType;
  trigger_type: AlertTriggerType;
  minimum_likelihood: number | null;
  minimum_severity: Exclude<Severity, "unknown"> | null;
  enabled: boolean;
  created_at: string;
}

export interface CreateAlertRuleRequest {
  name: string;
  hazard: HazardType;
  trigger_type: AlertTriggerType;
  asset_id?: string | null;
  minimum_likelihood?: number;
  minimum_severity?: Exclude<Severity, "unknown">;
  enabled?: boolean;
}

export interface AlertEvent {
  id: string;
  project_id: string;
  rule_id: string;
  asset_id: string | null;
  analysis_id: string;
  hazard: HazardType;
  event_kind: AlertEventKind;
  summary: string;
  evidence_ids: string[];
  delivery_status: AlertDeliveryStatus;
  created_at: string;
}

export interface NotificationChannel {
  id: string;
  project_id: string;
  name: string;
  kind: NotificationChannelKind;
  target: string;
  enabled: boolean;
  delivery_mode: NotificationDeliveryMode;
  has_secret_reference: boolean;
  created_at: string;
}

export interface CreateNotificationChannelRequest {
  name: string;
  kind: NotificationChannelKind;
  target: string;
  enabled?: boolean;
  delivery_mode?: NotificationDeliveryMode;
  secret_reference?: string | null;
}

export interface NotificationDispatchReceipt {
  id: string;
  project_id: string;
  alert_event_id: string;
  channel_id: string;
  status: NotificationReceiptStatus;
  created_at: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface EvaluateAlertRuleRequest {
  analysis_ids: string[];
}

export interface SourceEvidenceContract {
  requires_model_version: boolean;
  requires_raw_extract: boolean;
  required_query_keys: string[];
  required_unit_keys: string[];
}

export interface SourceHealthRecord {
  id: string;
  provider: string;
  dataset: string;
  capabilities: SourceCapability[];
  implementation: SourceImplementationState;
  remote_probe_policy: RemoteProbePolicy;
  evidence_contract: SourceEvidenceContract;
  limitations: string[];
  status: SourceHealthStatus;
  checked_at: string;
  remote_checked: boolean;
  message: string;
  details: Record<string, string | number | boolean | null>;
}

export interface SourceHealthResponse {
  generated_at: string;
  sources: SourceHealthRecord[];
  limitations: string[];
}

export interface AlertEvaluationSkip {
  analysis_id: string;
  reason: string;
}

export interface AlertEvaluationResult {
  rule: AlertRule;
  events: AlertEvent[];
  created_count: number;
  existing_count: number;
  skipped: AlertEvaluationSkip[];
  limitations: string[];
}

export type CreateSiteRequest = SiteInput;

export interface CompareRequest {
  analysis_ids?: string[];
}

export interface ComparisonItem {
  analysis_id: string;
  site_name: string;
  status: AnalysisStatus;
  mode: AnalysisMode | null;
  decision: Decision | null;
  findings: HazardFinding[];
}

export interface CompareResponse {
  comparison: ComparisonKind;
  analyses: ComparisonItem[];
  limitations: string[];
}

export interface ApiProblem {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: unknown;
  };
}
