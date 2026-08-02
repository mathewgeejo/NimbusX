import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { AnalysisEvidence, EvidenceRecord } from "../api/contracts";
import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  PageHeader,
  RouteLink
} from "../components/ui";
import { AnalysisWorkspaceNav } from "../components/workspaceNavigation";
import { displayCalendarDate, displayDateTime } from "../lib/time";

function QueryDetails(props: { evidence: EvidenceRecord }) {
  return (
    <details>
      <summary>Query parameters</summary>
      <pre>{JSON.stringify(props.evidence.query, null, 2)}</pre>
    </details>
  );
}

export function EvidenceView(props: { analysisId: string; navigate: (to: string) => void }) {
  const [data, setData] = useState<AnalysisEvidence | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await api.getEvidence(props.analysisId));
    } catch (requestError) {
      setError(requestError);
    }
  }, [props.analysisId]);

  useEffect(() => {
    void load();
  }, [load]);

  const analysisPath = "/analyses/" + props.analysisId;

  return (
    <>
      <PageHeader
        eyebrow="Evidence"
        title={"Provenance for analysis " + props.analysisId}
        description="Every source record includes its dataset, query, retrieval time, resolution, units, attribution, and content hash."
        actions={
          <div className="button-group">
            <button className="button button--secondary" type="button" onClick={() => void load()}>
              Refresh
            </button>
            <RouteLink className="button button--secondary" to={analysisPath} navigate={props.navigate}>
              Back to assessment
            </RouteLink>
          </div>
        }
      />

      {!data && !error ? <LoadingPanel label="Loading evidence records…" /> : null}
      <AnalysisWorkspaceNav analysisId={props.analysisId} active="evidence" navigate={props.navigate} />
      {error ? <ErrorPanel error={error} onRetry={() => void load()} /> : null}
      {data && data.evidence.length === 0 ? (
        <EmptyState title="No evidence records returned">
          An assessment without traceable evidence should not be treated as a complete result. Return to the
          assessment to review its data gaps and limitations.
        </EmptyState>
      ) : null}
      {data && data.evidence.length > 0 ? (
        <section className="surface" aria-labelledby="evidence-table-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Content-hashed source references</p>
              <h2 id="evidence-table-title">{data.evidence.length} evidence record{data.evidence.length === 1 ? "" : "s"}</h2>
            </div>
          </div>
          <div className="table-scroll">
            <table>
              <caption>Source evidence retrieved for this assessment</caption>
              <thead>
                <tr>
                  <th scope="col">Provider / dataset</th>
                  <th scope="col">Coverage and retrieval</th>
                  <th scope="col">Resolution / units</th>
                  <th scope="col">Integrity and use</th>
                  <th scope="col">Query</th>
                </tr>
              </thead>
              <tbody>
                {data.evidence.map((record) => (
                  <tr key={record.id}>
                    <th scope="row">
                      {record.provider}
                      <span className="table-detail">{record.dataset}</span>
                      {record.model_version ? <span className="table-detail">Model: {record.model_version}</span> : null}
                    </th>
                    <td>
                      {record.coverage_start || record.coverage_end
                        ? displayCalendarDate(record.coverage_start) + " to " + displayCalendarDate(record.coverage_end)
                        : "Coverage not specified"}
                      <span className="table-detail">Retrieved {displayDateTime(record.retrieved_at)}</span>
                    </td>
                    <td>
                      {record.resolution}
                      <span className="table-detail">{JSON.stringify(record.units)}</span>
                    </td>
                    <td>
                      <span className="table-detail">Hash: {record.content_hash}</span>
                      <span className="table-detail">
                        {record.raw_available
                          ? "Raw material is available only to the current development process and is not sent to this browser; it is lost when the API restarts."
                          : "Raw material is not available for this record."}
                      </span>
                      <span className="table-detail">{record.license}</span>
                      <span className="table-detail">{record.attribution}</span>
                    </td>
                    <td>
                      <QueryDetails evidence={record} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </>
  );
}
