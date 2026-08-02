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
  | (AnalysisRequestOptions & { site: SiteInput; site_id?: never })
  | (AnalysisRequestOptions & { site_id: string; site?: never });

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

export interface Analysis {
  id: string;
  status: AnalysisStatus;
  mode: AnalysisMode;
  project_id: string | null;
  resolved_mode: AnalysisMode | null;
  created_at: string;
  generated_at: string | null;
  expires_at: string | null;
  source_freshness: SourceFreshness[];
  site: SiteInput;
  window: TimeWindow;
  findings: HazardFinding[];
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