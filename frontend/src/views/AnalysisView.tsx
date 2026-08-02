import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Analysis, HazardFinding } from "../api/contracts";
import {
  DecisionPill,
  DefinitionList,
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  Notice,
  PageHeader,
  RouteLink,
  StatusPill
} from "../components/ui";
import { displayLikelihood, displayValue, titleCase } from "../lib/format";
import { displayDateTime } from "../lib/time";

const POLL_INTERVAL_MS = 3_000;

function isPending(status: Analysis["status"]): boolean {
  return status === "queued" || status === "running";
}

function thresholdLabel(operator: HazardFinding["operator"]): string {
  switch (operator) {
    case ">=":
      return "At least";
    case "<=":
      return "At most";
    case "observed":
      return "Observed";
  }
}

function statusNotice(analysis: Analysis) {
  switch (analysis.status) {
    case "queued":
      return (
        <Notice tone="info" title="Assessment queued">
          <p>
            No hazard conclusion has been made yet. NimbusX will wait for the orchestrator and source
            providers before presenting evidence.
          </p>
        </Notice>
      );
    case "running":
      return (
        <Notice tone="info" title="Assessment running">
          <p>
            Source evidence and deterministic hazard calculations are in progress. This page refreshes
            while the job is active.
          </p>
        </Notice>
      );
    case "partial":
      return (
        <Notice tone="warning" title="Partial assessment">
          <p>
            One or more inputs or providers were unavailable. Review data gaps, limitations, and evidence
            before relying on any listed finding.
          </p>
        </Notice>
      );
    case "failed":
      return (
        <Notice tone="error" title="Assessment failed">
          <p>
            The analysis did not produce source-backed findings. Review the returned data gaps and
            limitations before retrying it.
          </p>
        </Notice>
      );
    case "expired":
      return (
        <Notice tone="warning" title="Assessment expired">
          <p>
            This result is no longer current for its source freshness policy. Run a new assessment before
            treating it as operational evidence.
          </p>
        </Notice>
      );
    default:
      return null;
  }
}

export function AnalysisView(props: { analysisId: string; navigate: (to: string) => void }) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer: number | undefined;

    async function poll() {
      try {
        const result = await api.getAnalysis(props.analysisId, controller.signal);
        if (controller.signal.aborted) {
          return;
        }
        setAnalysis(result);
        setError(null);
        if (isPending(result.status)) {
          timer = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    setLoading(true);
    void poll();
    return () => {
      controller.abort();
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [props.analysisId, refreshKey]);

  const findings = analysis?.findings ?? [];
  const evidencePath = "/analyses/" + props.analysisId + "/evidence";
  const canDisplayFindings =
    analysis?.status === "complete" || analysis?.status === "partial" || analysis?.status === "expired";

  return (
    <>
      <PageHeader
        eyebrow="Assessment"
        title={analysis?.site.name ?? "Source-backed assessment"}
        description="A result is only as complete as its source evidence. Review status, limitations, and provenance before using it operationally."
        actions={
          <div className="button-group">
            <button
              className="button button--secondary"
              type="button"
              onClick={() => setRefreshKey((value) => value + 1)}
            >
              Refresh status
            </button>
            <RouteLink className="button button--secondary" to={evidencePath} navigate={props.navigate}>
              Evidence
            </RouteLink>
          </div>
        }
      />

      {loading && !analysis ? <LoadingPanel label="Loading assessment status..." /> : null}
      {error ? <ErrorPanel error={error} onRetry={() => setRefreshKey((value) => value + 1)} /> : null}
      {!analysis ? null : (
        <>
          <section className="surface assessment-summary" aria-labelledby="assessment-summary-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Assessment status</p>
                <h2 id="assessment-summary-title">Analysis {analysis.id}</h2>
              </div>
              <StatusPill status={analysis.status} />
            </div>
            <p className="visually-hidden" aria-live="polite">
              Assessment status: {titleCase(analysis.status)}
            </p>
            {statusNotice(analysis)}
            <DefinitionList
              items={[
                {
                  term: "Requested mode",
                  description: titleCase(analysis.mode)
                },
                {
                  term: "Resolved mode",
                  description: analysis.resolved_mode ? titleCase(analysis.resolved_mode) : "Pending"
                },
                {
                  term: "Window",
                  description:
                    displayDateTime(analysis.window.start) + " to " + displayDateTime(analysis.window.end)
                },
                {
                  term: "Generated",
                  description: displayDateTime(analysis.generated_at)
                },
                {
                  term: "Expires",
                  description: displayDateTime(analysis.expires_at)
                },
                {
                  term: "Decision",
                  description: (
                    <>
                      <DecisionPill decision={analysis.decision} />
                      {analysis.decision ? (
                        <span className="table-detail">{analysis.decision.rationale}</span>
                      ) : null}
                    </>
                  )
                }
              ]}
            />
          </section>

          {canDisplayFindings ? (
            <section className="surface" aria-labelledby="findings-title">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Hazard findings</p>
                  <h2 id="findings-title">Defined metrics, thresholds, and supporting evidence</h2>
                </div>
                <RouteLink className="text-link" to={evidencePath} navigate={props.navigate}>
                  Inspect provenance
                </RouteLink>
              </div>
              {findings.length === 0 ? (
                <EmptyState title="No hazard findings returned">
                  The API did not provide source-backed findings. Treat this assessment as insufficient
                  evidence and review its data gaps.
                </EmptyState>
              ) : (
                <div className="table-scroll">
                  <table>
                    <caption>Hazard findings returned by the analysis service</caption>
                    <thead>
                      <tr>
                        <th scope="col">Hazard</th>
                        <th scope="col">Defined event</th>
                        <th scope="col">Likelihood or observed value</th>
                        <th scope="col">Finding status</th>
                        <th scope="col">Calibration</th>
                        <th scope="col">Evidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {findings.map((finding, index) => (
                        <tr key={finding.hazard + "-" + index}>
                          <th scope="row">{titleCase(finding.hazard)}</th>
                          <td>
                            <strong>{titleCase(finding.metric)}</strong>
                            <span className="table-detail">{finding.event_definition}</span>
                            <span className="table-detail">
                              Threshold: {thresholdLabel(finding.operator)} {displayValue(finding.threshold, finding.unit)}
                            </span>
                          </td>
                          <td>
                            <strong>{displayLikelihood(finding.likelihood)}</strong>
                            {finding.observed_value !== null ? (
                              <span className="table-detail">
                                Observed: {displayValue(finding.observed_value, finding.unit)}
                              </span>
                            ) : null}
                            {finding.likelihood_basis ? (
                              <span className="table-detail">{finding.likelihood_basis}</span>
                            ) : null}
                            {finding.sample_size !== null ? (
                              <span className="table-detail">Sample size: {finding.sample_size}</span>
                            ) : null}
                          </td>
                          <td>
                            {titleCase(finding.status)}
                            <span className="table-detail">Severity: {titleCase(finding.severity)}</span>
                          </td>
                          <td>
                            {titleCase(finding.calibration_status)}
                            {finding.limitation ? (
                              <span className="table-detail">{finding.limitation}</span>
                            ) : null}
                          </td>
                          <td>
                            {finding.evidence_ids.length > 0 ? (
                              <RouteLink className="text-link" to={evidencePath} navigate={props.navigate}>
                                {finding.evidence_ids.length} record
                                {finding.evidence_ids.length === 1 ? "" : "s"}
                              </RouteLink>
                            ) : (
                              "Not linked"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {findings.some((finding) => finding.recommendation) ? (
                <div className="recommendations">
                  <h3>Actions supplied with findings</h3>
                  <ul className="text-list">
                    {findings
                      .filter((finding) => finding.recommendation)
                      .map((finding, index) => (
                        <li key={finding.hazard + "-action-" + index}>
                          <strong>{titleCase(finding.hazard)}:</strong> {finding.recommendation}
                        </li>
                      ))}
                  </ul>
                </div>
              ) : null}
            </section>
          ) : null}

          <div className="two-column">
            <section className="surface" aria-labelledby="gaps-title">
              <p className="eyebrow">Data quality</p>
              <h2 id="gaps-title">Gaps and limitations</h2>
              {analysis.data_gaps.length === 0 && analysis.limitations.length === 0 ? (
                <p className="subtle">No gaps or limitations were returned by the API.</p>
              ) : (
                <>
                  {analysis.data_gaps.length > 0 ? (
                    <>
                      <h3>Data gaps</h3>
                      <ul className="text-list">
                        {analysis.data_gaps.map((gap) => (
                          <li key={gap}>{gap}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                  {analysis.limitations.length > 0 ? (
                    <>
                      <h3>Limitations</h3>
                      <ul className="text-list">
                        {analysis.limitations.map((limitation) => (
                          <li key={limitation}>{limitation}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                </>
              )}
            </section>

            <section className="surface" aria-labelledby="source-freshness-title">
              <p className="eyebrow">Source freshness</p>
              <h2 id="source-freshness-title">Provider retrieval status</h2>
              {analysis.source_freshness.length === 0 ? (
                <p className="subtle">No source freshness metadata has been returned yet.</p>
              ) : (
                <ul className="source-list">
                  {analysis.source_freshness.map((source, index) => (
                    <li key={source.provider + "-" + index}>
                      <strong>{source.provider}</strong>
                      <span>{titleCase(source.status)}</span>
                      {source.retrieved_at ? <small>Retrieved {displayDateTime(source.retrieved_at)}</small> : null}
                      {source.valid_until ? <small>Valid until {displayDateTime(source.valid_until)}</small> : null}
                      {source.message ? <small>{source.message}</small> : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="action-strip" aria-label="Assessment tools">
            <RouteLink
              className="button button--secondary"
              to={"/analyses/" + analysis.id + "/compare"}
              navigate={props.navigate}
            >
              Review selected assessments
            </RouteLink>
            <RouteLink
              className="button button--secondary"
              to={"/analyses/" + analysis.id + "/report"}
              navigate={props.navigate}
            >
              Export report
            </RouteLink>
            <RouteLink className="button button--primary" to="/assessments/new" navigate={props.navigate}>
              New assessment
            </RouteLink>
          </section>
        </>
      )}
    </>
  );
}