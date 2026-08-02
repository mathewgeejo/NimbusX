import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { Analysis, Site } from "../api/contracts";
import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  Notice,
  PageHeader,
  RouteLink,
  StatusPill
} from "../components/ui";
import { titleCase } from "../lib/format";
import { displayDateTime, isValidIanaTimeZone } from "../lib/time";

interface SiteForm {
  name: string;
  latitude: string;
  longitude: string;
  timezone: string;
}

const defaultTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

export function ProjectView(props: { projectId: string; navigate: (to: string) => void }) {
  const [form, setForm] = useState<SiteForm>({
    name: "",
    latitude: "",
    longitude: "",
    timezone: defaultTimezone
  });
  const [createdSite, setCreatedSite] = useState<Site | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [analyses, setAnalyses] = useState<Analysis[] | null>(null);
  const [analysisError, setAnalysisError] = useState<unknown>(null);

  const loadAnalyses = useCallback(async () => {
    setAnalysisError(null);
    try {
      setAnalyses(await api.listProjectAnalyses(props.projectId));
    } catch (requestError) {
      setAnalysisError(requestError);
    }
  }, [props.projectId]);

  useEffect(() => {
    void loadAnalyses();
  }, [loadAnalyses]);

  function updateField(key: keyof SiteForm, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function validate(): { latitude: number; longitude: number } | null {
    const latitude = Number(form.latitude);
    const longitude = Number(form.longitude);

    if (!form.name.trim()) {
      setError(new Error("Enter a site name."));
      return null;
    }
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
      setError(new Error("Latitude must be a number from -90 to 90. Zero is valid."));
      return null;
    }
    if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      setError(new Error("Longitude must be a number from -180 to 180. Zero is valid."));
      return null;
    }
    if (!isValidIanaTimeZone(form.timezone.trim())) {
      setError(new Error("Use an IANA time zone such as Asia/Kolkata or America/New_York."));
      return null;
    }
    return { latitude, longitude };
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const coordinates = validate();
    if (!coordinates) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setCreatedSite(null);
    try {
      const site = await api.createSite(props.projectId, {
        name: form.name.trim(),
        latitude: coordinates.latitude,
        longitude: coordinates.longitude,
        timezone: form.timezone.trim()
      });
      setCreatedSite(site);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 404) {
        setError(
          new Error(
            "This project was not found in the current development workspace. Return to the portfolio and create or select a project."
          )
        );
      } else {
        setError(requestError);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Project workspace"
        title="Add an assessment location"
        description="A point site is required before NimbusX can query its source providers. Project-linked assessments can be reviewed below while this development process is running."
        actions={
          <RouteLink className="button button--secondary" to="/portfolio" navigate={props.navigate}>
            Back to portfolio
          </RouteLink>
        }
      />

      <div className="two-column two-column--wide-first">
        <section className="surface" aria-labelledby="site-form-title">
          <p className="eyebrow">Point site</p>
          <h2 id="site-form-title">Location details</h2>
          <form className="stack-form" onSubmit={(event) => void submit(event)} noValidate>
            <label htmlFor="site-name">
              Site name
              <input
                id="site-name"
                value={form.name}
                onChange={(event) => updateField("name", event.target.value)}
                maxLength={160}
                autoComplete="off"
                required
              />
            </label>
            <div className="form-grid">
              <label htmlFor="site-latitude">
                Latitude
                <input
                  id="site-latitude"
                  inputMode="decimal"
                  value={form.latitude}
                  onChange={(event) => updateField("latitude", event.target.value)}
                  placeholder="e.g. 19.0760"
                  required
                />
              </label>
              <label htmlFor="site-longitude">
                Longitude
                <input
                  id="site-longitude"
                  inputMode="decimal"
                  value={form.longitude}
                  onChange={(event) => updateField("longitude", event.target.value)}
                  placeholder="e.g. 72.8777"
                  required
                />
              </label>
            </div>
            <label htmlFor="site-timezone">
              Local IANA time zone
              <input
                id="site-timezone"
                value={form.timezone}
                onChange={(event) => updateField("timezone", event.target.value)}
                placeholder="e.g. Asia/Kolkata"
                spellCheck="false"
                required
              />
              <span className="field-hint">
                Dates are interpreted in this zone, not silently in the analyst&apos;s browser time zone.
              </span>
            </label>
            {error ? <ErrorPanel error={error} /> : null}
            {createdSite ? (
              <Notice tone="success" title="Site saved">
                <p>
                  {createdSite.name} is available for a point assessment. Its identifier is <code>{createdSite.id}</code>.
                  Supply that ID with this project in the assessment builder to preserve the association.
                </p>
              </Notice>
            ) : null}
            <button className="button button--primary" type="submit" disabled={submitting}>
              {submitting ? "Saving site..." : "Save site"}
            </button>
          </form>
        </section>

        <aside className="surface surface--muted" aria-labelledby="site-boundaries-title">
          <p className="eyebrow">Scope</p>
          <h2 id="site-boundaries-title">What this version supports</h2>
          <ul className="text-list">
            <li>This form creates point sites for source-backed assessment.</li>
            <li>The API may store a validated polygon geometry for a future spatial workflow, but V1 rejects polygon analyses because it has no spatial aggregation adapter.</li>
            <li>Address search, polygon drawing, and CSV/GeoJSON portfolio import are not available in this foundation.</li>
          </ul>
          <p className="subtle">
            Flood and wildfire exposure are deliberately not inferred from a point location in this version.
          </p>
        </aside>
      </div>

      <section className="surface" aria-labelledby="project-assessments-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Project-linked assessments</p>
            <h2 id="project-assessments-title">Saved in this development process</h2>
          </div>
          <button className="button button--secondary" type="button" onClick={() => void loadAnalyses()}>
            Refresh
          </button>
        </div>
        {analyses === null && !analysisError ? <LoadingPanel label="Loading project assessments..." /> : null}
        {analysisError ? <ErrorPanel error={analysisError} onRetry={() => void loadAnalyses()} /> : null}
        {analyses && analyses.length === 0 ? (
          <EmptyState title="No project-linked assessments yet">
            Create an assessment with this project ID and a point site to list it here.
          </EmptyState>
        ) : null}
        {analyses && analyses.length > 0 ? (
          <div className="table-scroll">
            <table>
              <caption>Assessments associated with this project</caption>
              <thead>
                <tr>
                  <th scope="col">Site</th>
                  <th scope="col">Mode</th>
                  <th scope="col">Status</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((analysis) => (
                  <tr key={analysis.id}>
                    <th scope="row">
                      <RouteLink to={"/analyses/" + analysis.id} navigate={props.navigate} className="text-link">
                        {analysis.site.name}
                      </RouteLink>
                    </th>
                    <td>{titleCase(analysis.resolved_mode ?? analysis.mode)}</td>
                    <td><StatusPill status={analysis.status} /></td>
                    <td>{displayDateTime(analysis.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </>
  );
}