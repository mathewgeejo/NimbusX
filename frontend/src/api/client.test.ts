import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";

describe("NimbusX API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses the versioned analysis endpoint, preserves zero coordinates, and avoids cross-origin credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "analysis-1",
          status: "queued",
          mode: "auto",
          created_at: "2026-08-02T00:00:00Z"
        }),
        { status: 202, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await api.createAnalysis({
      mode: "auto",
      window: { start: "2026-08-02T00:00:00Z", end: "2026-08-03T00:00:00Z" },
      site: {
        name: "Equator site",
        latitude: 0,
        longitude: 0,
        timezone: "UTC"
      }
    });

    expect(response.status).toBe("queued");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/analyses",
      expect.objectContaining({ method: "POST", credentials: "same-origin" })
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toMatchObject({
      site: { latitude: 0, longitude: 0 }
    });
  });

  it("preserves structured API errors rather than fabricating a result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "provider_unavailable",
              message: "The forecast provider is unavailable.",
              request_id: "req-1"
            }
          }),
          { status: 503, headers: { "content-type": "application/json" } }
        )
      )
    );

    await expect(api.getAnalysis("analysis-1")).rejects.toEqual(
      expect.objectContaining({
        name: "ApiError",
        code: "provider_unavailable",
        status: 503,
        requestId: "req-1"
      })
    );
  });

  it("accepts the complete v1 assessment shape, including null scientific values", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "analysis-1",
            status: "partial",
            mode: "auto",
            project_id: null,
            asset_id: null,
            resolved_mode: "observed",
            created_at: "2026-08-02T00:00:00Z",
            generated_at: "2026-08-02T00:01:00Z",
            expires_at: null,
            source_freshness: [
              {
                provider: "NASA POWER",
                status: "current",
                retrieved_at: "2026-08-02T00:01:00Z",
                valid_until: null,
                message: null
              }
            ],
            site: {
              name: "Equator site",
              latitude: 0,
              longitude: 0,
              timezone: "UTC",
              geometry: null,
              address: null
            },
            window: { start: "2026-08-01T00:00:00Z", end: "2026-08-01T23:59:59Z" },
            findings: [
              {
                hazard: "extreme_heat",
                status: "available",
                metric: "daily_maximum_temperature",
                operator: ">=",
                threshold: 35,
                unit: "degC",
                event_definition: "P(local-day maximum temperature >= 35 degC)",
                likelihood: null,
                likelihood_basis: null,
                observed_value: 33.4,
                sample_size: 1,
                severity: "low",
                calibration_status: "not_applicable",
                recommendation: null,
                evidence_ids: ["evidence-1"],
                limitation: null
              }
            ],
            operational_findings: [],
            decision: null,
            evidence_ids: ["evidence-1"],
            data_gaps: ["Wind observation was unavailable."],
            limitations: ["No decision is issued without a complete asset context."],
            report_version: "1.0"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const analysis = await api.getAnalysis("analysis-1");

    expect(analysis.findings[0].observed_value).toBe(33.4);
    expect(analysis.findings[0].likelihood).toBeNull();
    expect(analysis.resolved_mode).toBe("observed");
  });
  it("rejects a malformed success response instead of displaying a guessed assessment", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ id: "analysis-1", status: "complete" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    await expect(api.getAnalysis("analysis-1")).rejects.toEqual(
      expect.objectContaining({ name: "ApiError", code: "invalid_response", status: 200 })
    );
  });

  it("preserves an aborted request so route cleanup does not show a network error", async () => {
    const abortError = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortError));

    await expect(api.getAnalysis("analysis-1", new AbortController().signal)).rejects.toBe(abortError);
  });

  it("decodes versioned asset templates before exposing them to the workspace", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: "data_center",
            display_name: "Data center",
            description: "Critical digital infrastructure.",
            required_exposure_fields: [
              {
                key: "service_criticality",
                label: "Service criticality",
                description: "Criticality of supported services.",
                value_type: "enum",
                allowed_values: ["standard", "critical"],
                required: true
              }
            ],
            required_vulnerability_fields: [],
            supported_hazards: ["extreme_heat", "wind"],
            operational_rules: [
              {
                id: "data-center-heat-v1",
                name: "Heat continuity review",
                hazard: "extreme_heat",
                minimum_severity: "moderate",
                required_exposure_fields: ["service_criticality"],
                required_vulnerability_fields: [],
                action: "Review cooling capacity.",
                rationale: "Published screening rule."
              }
            ],
            version: "1.0"
          }
        ]),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const templates = await api.listAssetTemplates();

    expect(templates[0].operational_rules[0].minimum_severity).toBe("moderate");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/asset-templates",
      expect.objectContaining({ credentials: "same-origin" })
    );
  });

  it("rejects malformed alert events instead of inventing delivery state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify([
            {
              id: "event-1",
              project_id: "project-1",
              rule_id: "rule-1",
              asset_id: null,
              analysis_id: "analysis-1",
              hazard: "extreme_heat",
              event_kind: "severity_trigger",
              summary: "Needs review",
              evidence_ids: [],
              delivery_status: "sent",
              created_at: "2026-08-02T00:00:00Z"
            }
          ]),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    await expect(api.listAlertEvents("project-1")).rejects.toEqual(
      expect.objectContaining({ name: "ApiError", code: "invalid_response" })
    );
  });

  it("decodes a safe notification receipt and never assumes an external send", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "receipt-1",
          project_id: "project-1",
          alert_event_id: "event-1",
          channel_id: "channel-1",
          status: "dry_run",
          created_at: "2026-08-02T00:00:00Z",
          message: "Dry run recorded; no external notification was sent.",
          payload: { alert_event_id: "event-1", evidence_ids: ["evidence-1"] }
        }),
        { status: 201, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const receipt = await api.dispatchAlertEvent("project-1", "event-1", "channel-1");

    expect(receipt.status).toBe("dry_run");
    expect(receipt.message).toContain("no external notification");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/v1/projects/project-1/alert-events/event-1/notification-channels/channel-1/dispatch",
      expect.objectContaining({ method: "POST", credentials: "same-origin" })
    );
  });
});
