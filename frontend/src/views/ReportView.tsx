import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Analysis, ReportFormat } from "../api/contracts";
import { ErrorPanel, LoadingPanel, Notice, PageHeader, RouteLink } from "../components/ui";
import { AnalysisWorkspaceNav } from "../components/workspaceNavigation";

function filename(analysisId: string, format: ReportFormat): string {
  return "nimbusx-analysis-" + analysisId + "." + format;
}

export function ReportView(props: { analysisId: string; navigate: (to: string) => void }) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [downloadError, setDownloadError] = useState<unknown>(null);
  const [downloading, setDownloading] = useState<ReportFormat | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setAnalysis(await api.getAnalysis(props.analysisId));
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, [props.analysisId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function download(format: ReportFormat) {
    setDownloadError(null);
    setDownloading(format);
    try {
      const blob = await api.downloadReport(props.analysisId, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename(props.analysisId, format);
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setDownloadError(requestError);
    } finally {
      setDownloading(null);
    }
  }

  const analysisPath = "/analyses/" + props.analysisId;

  return (
    <>
      <PageHeader
        eyebrow="Report"
        title="Export the evidence you can inspect"
        description="JSON and CSV exports are produced on request from the structured analysis result. Inspect the separate evidence view before relying on an export; PDF is not offered until a reproducible renderer is available."
        actions={
          <RouteLink className="button button--secondary" to={analysisPath} navigate={props.navigate}>
            Back to assessment
          </RouteLink>
        }
      />
      {loading ? <LoadingPanel label="Checking report availability…" /> : null}
      <AnalysisWorkspaceNav analysisId={props.analysisId} active="report" navigate={props.navigate} />
      {error ? <ErrorPanel error={error} onRetry={() => void load()} /> : null}
      {analysis ? (
        <section className="surface report-panel" aria-labelledby="report-version-title">
          <p className="eyebrow">Available exports</p>
          <h2 id="report-version-title">Analysis report version {analysis.report_version}</h2>
          <DefinitionRows analysis={analysis} />
          {analysis.status !== "complete" && analysis.status !== "partial" ? (
            <Notice tone="warning" title="Assessment is not ready">
              <p>
                A report may be incomplete while the assessment is {analysis.status}. Inspect the
                assessment status before distributing an export.
              </p>
            </Notice>
          ) : null}
          {downloadError ? <ErrorPanel error={downloadError} /> : null}
          <div className="button-group">
            <button
              className="button button--primary"
              type="button"
              disabled={downloading !== null}
              onClick={() => void download("json")}
            >
              {downloading === "json" ? "Preparing JSON…" : "Download JSON"}
            </button>
            <button
              className="button button--secondary"
              type="button"
              disabled={downloading !== null}
              onClick={() => void download("csv")}
            >
              {downloading === "csv" ? "Preparing CSV…" : "Download CSV"}
            </button>
          </div>
        </section>
      ) : null}
    </>
  );
}

function DefinitionRows(props: { analysis: Analysis }) {
  return (
    <dl className="definition-list">
      <div>
        <dt>Analysis identifier</dt>
        <dd>{props.analysis.id}</dd>
      </div>
      <div>
        <dt>Evidence references</dt>
        <dd>{props.analysis.evidence_ids.length}</dd>
      </div>
      <div>
        <dt>Result status</dt>
        <dd>{props.analysis.status}</dd>
      </div>
    </dl>
  );
}
