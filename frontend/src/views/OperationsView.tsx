import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { SourceHealthResponse } from "../api/contracts";
import { ErrorPanel, LoadingPanel, PageHeader, RouteLink } from "../components/ui";
import { titleCase } from "../lib/format";
import { displayDateTime } from "../lib/time";

interface ThresholdPattern {
  name: string;
  purpose: string;
  triggers: string[];
}

const thresholdPatterns: ThresholdPattern[] = [
  {
    name: "Observed threshold breach",
    purpose: "Records that a completed event window crossed an explicit operating limit.",
    triggers: ["Heat or cold threshold", "Precipitation threshold", "Daily mean 10 m wind threshold"]
  },
  {
    name: "Baseline likelihood",
    purpose: "Flags an event definition whose historical calendar-window likelihood meets a policy limit.",
    triggers: ["Empirical likelihood only", "Declared baseline period", "No probability relabelled from a percentile"]
  },
  {
    name: "Severity review",
    purpose: "Routes a source-backed hazard finding to human review at or above a chosen severity.",
    triggers: ["Low, moderate, or high finding severity", "No asset-risk verdict", "Evidence references retained"]
  }
];

export function OperationsView(props: { navigate: (to: string) => void }) {
  const [sourceHealth, setSourceHealth] = useState<SourceHealthResponse | null>(null);
  const [sourceError, setSourceError] = useState<unknown>(null);

  const loadSourceHealth = useCallback(async () => {
    setSourceError(null);
    try {
      setSourceHealth(await api.getSourceHealth());
    } catch (requestError) {
      setSourceError(requestError);
    }
  }, []);

  useEffect(() => {
    void loadSourceHealth();
  }, [loadSourceHealth]);

  return (
    <>
      <PageHeader
        eyebrow="Operations design"
        title="Define controls before you automate an alert"
        description="NimbusX separates source evidence, a hazard finding, and an operational response. A threshold is a review control, not a prediction or a risk certification."
        actions={
          <RouteLink className="button button--primary" to="/assessments/new" navigate={props.navigate}>
            Start an assessment
          </RouteLink>
        }
      />

      <section className="surface portfolio-intro" aria-labelledby="operations-principle-title">
        <div>
          <p className="eyebrow">Control model</p>
          <h2 id="operations-principle-title">Every operational rule should state the event, owner, and evidence it needs.</h2>
        </div>
        <p>
          This workspace does not convert a weather observation into an emergency instruction. Configure a
          review rule only after the asset owner has approved the threshold and follow-up process.
        </p>
      </section>

      <section className="surface" aria-labelledby="threshold-patterns-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Threshold patterns</p>
            <h2 id="threshold-patterns-title">Controls supported by the operational workspace</h2>
          </div>
        </div>
        <div className="pattern-grid">
          {thresholdPatterns.map((pattern) => (
            <article className="pattern-card" key={pattern.name}>
              <h3>{pattern.name}</h3>
              <p>{pattern.purpose}</p>
              <ul className="text-list">
                {pattern.triggers.map((trigger) => (
                  <li key={trigger}>{trigger}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <div className="two-column">
        <section className="surface" aria-labelledby="operating-sequence-title">
          <p className="eyebrow">Operating sequence</p>
          <h2 id="operating-sequence-title">Make the workflow reviewable</h2>
          <ol className="numbered-list">
            <li>Define the asset and its site, operating limit, and accountable owner.</li>
            <li>Run a source-backed assessment for the relevant window.</li>
            <li>Evaluate an enabled rule against completed evidence.</li>
            <li>Record the resulting event and follow the organization&apos;s approved response procedure.</li>
          </ol>
        </section>
        <section className="surface surface--muted" aria-labelledby="operating-boundaries-title">
          <p className="eyebrow">Boundary</p>
          <h2 id="operating-boundaries-title">What NimbusX will not infer</h2>
          <ul className="text-list">
            <li>No alert is sent from an unavailable provider or a fabricated forecast.</li>
            <li>No rule is an emergency-response order or a regulatory determination.</li>
            <li>Rules do not create an asset-risk verdict without a published decision policy.</li>
          </ul>
        </section>
      </div>

      <section className="surface source-health-panel" aria-labelledby="source-health-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Source catalog</p>
            <h2 id="source-health-title">Adapter implementation state</h2>
          </div>
          <button className="button button--secondary" type="button" onClick={() => void loadSourceHealth()}>
            Refresh
          </button>
        </div>
        <p className="subtle">
          This is a local configuration and implementation catalog, not a hidden live-provider probe.
          A source can establish retrieval availability only when an assessment actually retrieves it.
        </p>
        {!sourceHealth && !sourceError ? <LoadingPanel label="Loading source catalog..." /> : null}
        {sourceError ? <ErrorPanel error={sourceError} onRetry={() => void loadSourceHealth()} /> : null}
        {sourceHealth ? (
          <>
            <div className="table-scroll">
              <table>
                <caption>Configured source adapters and their implementation boundaries</caption>
                <thead>
                  <tr>
                    <th scope="col">Source</th>
                    <th scope="col">Capabilities</th>
                    <th scope="col">Implementation / state</th>
                    <th scope="col">Probe policy</th>
                    <th scope="col">Evidence requirements</th>
                  </tr>
                </thead>
                <tbody>
                  {sourceHealth.sources.map((source) => (
                    <tr key={source.id}>
                      <th scope="row">
                        {source.provider}
                        <span className="table-detail">{source.dataset}</span>
                        <span className="table-detail">Checked {displayDateTime(source.checked_at)}</span>
                      </th>
                      <td>{source.capabilities.map(titleCase).join(", ")}</td>
                      <td>
                        {titleCase(source.implementation)} / {titleCase(source.status)}
                        <span className="table-detail">{source.message}</span>
                      </td>
                      <td>
                        {titleCase(source.remote_probe_policy)}
                        <span className="table-detail">Remote checked: {source.remote_checked ? "Yes" : "No"}</span>
                      </td>
                      <td>
                        {source.evidence_contract.requires_raw_extract ? "Raw extract required" : "Raw extract optional"}
                        <span className="table-detail">
                          Query keys: {source.evidence_contract.required_query_keys.join(", ") || "None declared"}
                        </span>
                        <span className="table-detail">
                          Unit keys: {source.evidence_contract.required_unit_keys.join(", ") || "None declared"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {sourceHealth.limitations.length > 0 ? (
              <ul className="text-list">
                {sourceHealth.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
              </ul>
            ) : null}
          </>
        ) : null}
      </section>
    </>
  );
}
