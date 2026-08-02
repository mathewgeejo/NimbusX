import { FormEvent, useState } from "react";
import { ApiError, api } from "../api/client";
import type { CompareResponse } from "../api/contracts";
import { ErrorPanel, Notice, PageHeader, RouteLink, StatusPill } from "../components/ui";
import { AnalysisWorkspaceNav } from "../components/workspaceNavigation";
import { titleCase } from "../lib/format";

function idsFromInput(value: string): string[] {
  return value
    .split(/[\s,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function CompareView(props: { analysisId: string; navigate: (to: string) => void }) {
  const [analysisIds, setAnalysisIds] = useState("");
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const ids = idsFromInput(analysisIds);
      const response = await api.compareAnalysis(props.analysisId, {
        ...(ids.length > 0 ? { analysis_ids: ids } : {})
      });
      setResult(response);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) {
        setError(
          new Error(
            "The selected assessment summary is not available until every selected assessment reaches a terminal status."
          )
        );
      } else {
        setError(requestError);
      }
    } finally {
      setSubmitting(false);
    }
  }

  const backPath = "/analyses/" + props.analysisId;

  return (
    <>
      <PageHeader
        eyebrow="Assessment review"
        title="Review selected assessment summaries"
        description="This foundation lists terminal outputs side by side. It does not calculate aligned changes, deltas, or rankings by date, site, baseline, or scenario."
        actions={
          <RouteLink className="button button--secondary" to={backPath} navigate={props.navigate}>
            Back to assessment
          </RouteLink>
        }
      />
      <AnalysisWorkspaceNav analysisId={props.analysisId} active="compare" navigate={props.navigate} />
      <div className="two-column two-column--wide-first">
        <section className="surface" aria-labelledby="comparison-builder-title">
          <p className="eyebrow">Assessment selection</p>
          <h2 id="comparison-builder-title">Choose terminal assessments to review</h2>
          <form className="stack-form" onSubmit={(event) => void submit(event)}>
            <label htmlFor="comparison-analysis-ids">
              Other assessment IDs <span className="optional">optional</span>
              <textarea
                id="comparison-analysis-ids"
                value={analysisIds}
                onChange={(event) => setAnalysisIds(event.target.value)}
                rows={4}
                placeholder="Paste one or more UUIDs, separated by commas or new lines"
              />
              <span className="field-hint">Leave blank to review this assessment alone.</span>
            </label>
            {error ? <ErrorPanel error={error} /> : null}
            <button className="button button--primary" type="submit" disabled={submitting}>
              {submitting ? "Loading assessments..." : "Review assessments"}
            </button>
          </form>
        </section>
        <aside className="surface surface--muted" aria-labelledby="comparison-boundaries-title">
          <p className="eyebrow">Current boundary</p>
          <h2 id="comparison-boundaries-title">What this review means</h2>
          <ul className="text-list">
            <li>Only terminal assessments can be selected; queued and running work is rejected.</li>
            <li>Each assessment retains its own mode, source evidence, limitations, and calibration status.</li>
            <li>V1 does not infer a change or ranking from different dates, sites, thresholds, baselines, or scenarios.</li>
          </ul>
        </aside>
      </div>

      {result ? <ComparisonResult result={result} /> : null}
    </>
  );
}

function ComparisonResult(props: { result: CompareResponse }) {
  const { result } = props;
  return (
    <section className="surface comparison-result" aria-labelledby="comparison-result-title">
      <p className="eyebrow">Selected assessment summaries</p>
      <h2 id="comparison-result-title">Terminal outputs supplied by the API</h2>
      {result.analyses.length > 0 ? (
        <div className="table-scroll">
          <table>
            <caption>Selected terminal analysis summaries supplied by the API</caption>
            <thead>
              <tr>
                <th scope="col">Assessment</th>
                <th scope="col">Site</th>
                <th scope="col">Mode</th>
                <th scope="col">Status</th>
                <th scope="col">Decision</th>
                <th scope="col">Findings</th>
              </tr>
            </thead>
            <tbody>
              {result.analyses.map((analysis) => (
                <tr key={analysis.analysis_id}>
                  <th scope="row">{analysis.analysis_id}</th>
                  <td>{analysis.site_name}</td>
                  <td>{analysis.mode ? titleCase(analysis.mode) : "Not specified"}</td>
                  <td><StatusPill status={analysis.status} /></td>
                  <td>{analysis.decision ? titleCase(analysis.decision) : "No decision"}</td>
                  <td>{analysis.findings.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="subtle">The API returned no assessment summaries.</p>
      )}
      {result.limitations.length > 0 ? (
        <Notice tone="warning" title="Review limitations">
          <ul className="text-list">
            {result.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </Notice>
      ) : null}
    </section>
  );
}
