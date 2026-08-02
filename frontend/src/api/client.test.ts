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
});