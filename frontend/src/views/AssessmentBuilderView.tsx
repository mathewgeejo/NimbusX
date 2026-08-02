import { FormEvent, useState } from "react";
import { api } from "../api/client";
import type {
  AnalysisMode,
  AnalysisRequestOptions,
  CreateAnalysisRequest,
  HazardThresholds,
  Scenario
} from "../api/contracts";
import { ErrorPanel, Notice, PageHeader, RouteLink } from "../components/ui";
import { isValidIanaTimeZone, localDateTimeInZoneToIso } from "../lib/time";

interface BuilderForm {
  projectId: string;
  siteId: string;
  siteName: string;
  latitude: string;
  longitude: string;
  timezone: string;
  start: string;
  end: string;
  mode: AnalysisMode;
  assetTemplate: string;
  exposure: string;
  vulnerability: string;
  extremeHeat: string;
  extremeCold: string;
  heavyPrecipitation: string;
  windSpeed: string;
  droughtPrecipitation: string;
  baselineStart: string;
  baselineEnd: string;
}

function localDateTimeValue(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function initialForm(): BuilderForm {
  const now = new Date();
  const end = new Date(now.getTime() + 24 * 60 * 60 * 1000);
  return {
    projectId: "",
    siteId: "",
    siteName: "",
    latitude: "",
    longitude: "",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    start: localDateTimeValue(now),
    end: localDateTimeValue(end),
    mode: "auto",
    assetTemplate: "",
    exposure: "",
    vulnerability: "",
    extremeHeat: "",
    extremeCold: "",
    heavyPrecipitation: "",
    windSpeed: "",
    droughtPrecipitation: "",
    baselineStart: "1991",
    baselineEnd: "2020"
  };
}

const modeDescriptions: Record<AnalysisMode, string> = {
  auto: "Routes by the event date. The returned resolved mode states what the system actually evaluated.",
  observed: "Past observation/reanalysis only. It reports available source coverage and latency.",
  forecast: "Operational forecast only for a provider-supported near-term window. The ECMWF adapter is not implemented in this foundation, so this request returns insufficient evidence rather than a substitute.",
  seasonal: "Seasonal outlook only. The calibrated Copernicus adapter is not implemented in this foundation, so this request returns insufficient evidence rather than a substitute.",
  baseline: "Historical daily baseline for the requested local calendar window, not a future daily forecast.",
  scenario: "Long-term scenario analysis only. This foundation reports insufficient evidence because its multi-model source adapter is not implemented."
};

export function AssessmentBuilderView(props: { navigate: (to: string) => void }) {
  const [form, setForm] = useState<BuilderForm>(initialForm);
  const [scenarios, setScenarios] = useState<Scenario[]>([
    "ssp126",
    "ssp245",
    "ssp585"
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  function updateField(field: keyof BuilderForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function numberOrUndefined(
    value: string,
    label: string,
    minimum?: number,
    maximum?: number
  ): number | undefined {
    if (value.trim() === "") {
      return undefined;
    }
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      throw new Error(label + " must be a valid number.");
    }
    if (minimum !== undefined && parsed < minimum) {
      throw new Error(label + " must be at least " + minimum + ".");
    }
    if (maximum !== undefined && parsed > maximum) {
      throw new Error(label + " must be at most " + maximum + ".");
    }
    return parsed;
  }

  function buildThresholds(): HazardThresholds | undefined {
    const thresholds: HazardThresholds = {
      extreme_heat_c: numberOrUndefined(form.extremeHeat, "Extreme heat threshold", -90, 80),
      extreme_cold_c: numberOrUndefined(form.extremeCold, "Extreme cold threshold", -90, 50),
      heavy_precipitation_mm: numberOrUndefined(
        form.heavyPrecipitation,
        "Heavy precipitation threshold",
        0,
        5000
      ),
      wind_speed_m_s: numberOrUndefined(form.windSpeed, "Wind threshold", 0, 200),
      drought_precipitation_mm: numberOrUndefined(
        form.droughtPrecipitation,
        "Drought threshold",
        0,
        5000
      )
    };

    return Object.values(thresholds).some((value) => value !== undefined) ? thresholds : undefined;
  }

  function buildRequest(): CreateAnalysisRequest {
    const timezone = form.timezone.trim();
    if (!isValidIanaTimeZone(timezone)) {
      throw new Error("Use an IANA time zone such as Asia/Kolkata or America/New_York.");
    }

    const start = localDateTimeInZoneToIso(form.start, timezone);
    const end = localDateTimeInZoneToIso(form.end, timezone);
    if (new Date(start).getTime() > new Date(end).getTime()) {
      throw new Error("The assessment end cannot precede its start.");
    }

    const request: AnalysisRequestOptions = {
      window: { start, end },
      mode: form.mode
    };
    const thresholds = buildThresholds();
    if (thresholds) {
      request.thresholds = thresholds;
    }
    if (form.projectId.trim()) {
      request.project_id = form.projectId.trim();
    }

    const hasAssetInput =
      form.assetTemplate.trim() !== "" || form.exposure.trim() !== "" || form.vulnerability.trim() !== "";
    if (hasAssetInput) {
      request.asset = {
        ...(form.assetTemplate.trim() ? { template: form.assetTemplate.trim() } : {}),
        ...(form.exposure.trim() ? { exposure: { description: form.exposure.trim() } } : {}),
        ...(form.vulnerability.trim() ? { vulnerability: { description: form.vulnerability.trim() } } : {})
      };
    }

    if (form.mode === "baseline" || form.mode === "scenario") {
      const startYear = numberOrUndefined(form.baselineStart, "Baseline start year", 1981, 2100);
      const endYear = numberOrUndefined(form.baselineEnd, "Baseline end year", 1981, 2100);
      if (
        startYear === undefined ||
        endYear === undefined ||
        !Number.isInteger(startYear) ||
        !Number.isInteger(endYear) ||
        startYear > endYear
      ) {
        throw new Error("Enter a valid baseline period with a start year no later than its end year.");
      }
      request.baseline = { start_year: startYear, end_year: endYear };
    }

    if (form.mode === "scenario") {
      if (scenarios.length === 0) {
        throw new Error("Choose at least one emissions scenario.");
      }
      request.scenarios = scenarios;
    }

    if (form.siteId.trim()) {
      return { ...request, site_id: form.siteId.trim() };
    }

    const latitude = Number(form.latitude);
    const longitude = Number(form.longitude);
    if (!form.siteName.trim()) {
      throw new Error("Enter a site name or provide an existing site identifier.");
    }
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
      throw new Error("Latitude must be a number from -90 to 90. Zero is valid.");
    }
    if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      throw new Error("Longitude must be a number from -180 to 180. Zero is valid.");
    }
    return {
      ...request,
      site: {
        name: form.siteName.trim(),
        latitude,
        longitude,
        timezone
      }
    };
  }

  function toggleScenario(scenario: Scenario) {
    setScenarios((current) =>
      current.includes(scenario)
        ? current.filter((item) => item !== scenario)
        : [...current, scenario]
    );
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    let request: CreateAnalysisRequest;
    try {
      request = buildRequest();
    } catch (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    try {
      const analysis = await api.createAnalysis(request);
      props.navigate("/analyses/" + analysis.id);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Assessment builder"
        title="Define a defensible assessment"
        description="Choose a site, an explicit local time window, and the analysis horizon. NimbusX returns only source-backed findings and records data gaps."
        actions={
          <RouteLink className="button button--secondary" to="/portfolio" navigate={props.navigate}>
            Portfolio
          </RouteLink>
        }
      />

      <form className="assessment-form" onSubmit={(event) => void submit(event)} noValidate>
        <section className="surface" aria-labelledby="site-input-title">
          <p className="eyebrow">1. Site and time window</p>
          <h2 id="site-input-title">Where and when</h2>
          <div className="form-grid form-grid--three">
            <label htmlFor="assessment-project-id">
              Project ID <span className="optional">optional</span>
              <input
                id="assessment-project-id"
                value={form.projectId}
                onChange={(event) => updateField("projectId", event.target.value)}
                placeholder="UUID from your portfolio"
                autoComplete="off"
              />
            </label>
            <label htmlFor="assessment-site-id">
              Existing site ID <span className="optional">optional</span>
              <input
                id="assessment-site-id"
                value={form.siteId}
                onChange={(event) => updateField("siteId", event.target.value)}
                placeholder="Use instead of new coordinates"
                autoComplete="off"
              />
            </label>
            <label htmlFor="assessment-timezone">
              Local IANA time zone
              <input
                id="assessment-timezone"
                value={form.timezone}
                onChange={(event) => updateField("timezone", event.target.value)}
                placeholder="Asia/Kolkata"
                spellCheck="false"
                required
              />
            </label>
          </div>
          {!form.siteId.trim() ? (
            <div className="form-grid form-grid--three">
              <label htmlFor="assessment-site-name">
                Site name
                <input
                  id="assessment-site-name"
                  value={form.siteName}
                  onChange={(event) => updateField("siteName", event.target.value)}
                  autoComplete="off"
                  required
                />
              </label>
              <label htmlFor="assessment-latitude">
                Latitude
                <input
                  id="assessment-latitude"
                  inputMode="decimal"
                  value={form.latitude}
                  onChange={(event) => updateField("latitude", event.target.value)}
                  required
                />
              </label>
              <label htmlFor="assessment-longitude">
                Longitude
                <input
                  id="assessment-longitude"
                  inputMode="decimal"
                  value={form.longitude}
                  onChange={(event) => updateField("longitude", event.target.value)}
                  required
                />
              </label>
            </div>
          ) : null}
          <div className="form-grid">
            <label htmlFor="assessment-start">
              Local start
              <input
                id="assessment-start"
                type="datetime-local"
                value={form.start}
                onChange={(event) => updateField("start", event.target.value)}
                required
              />
            </label>
            <label htmlFor="assessment-end">
              Local end
              <input
                id="assessment-end"
                type="datetime-local"
                value={form.end}
                onChange={(event) => updateField("end", event.target.value)}
                required
              />
            </label>
          </div>
          <p className="field-hint">
            NimbusX converts these site-local values to offset-aware API timestamps. Check DST boundary
            dates with your operational policy.
          </p>
        </section>

        <section className="surface" aria-labelledby="mode-title">
          <p className="eyebrow">2. Analysis horizon</p>
          <h2 id="mode-title">What kind of answer is appropriate?</h2>
          <label htmlFor="assessment-mode">
            Mode
            <select
              id="assessment-mode"
              value={form.mode}
              onChange={(event) => updateField("mode", event.target.value as AnalysisMode)}
            >
              <option value="auto">Auto-select from event date</option>
              <option value="observed">Observed / reanalysis</option>
              <option value="forecast">Operational forecast</option>
              <option value="seasonal">Seasonal outlook</option>
              <option value="baseline">Historical baseline</option>
              <option value="scenario">Scenario projection</option>
            </select>
          </label>
          <Notice tone="info" title={form.mode === "auto" ? "Automatic horizon routing" : "Selected mode"}>
            <p>{modeDescriptions[form.mode]}</p>
          </Notice>
        </section>

        <section className="surface" aria-labelledby="risk-inputs-title">
          <p className="eyebrow">3. Asset context and thresholds</p>
          <h2 id="risk-inputs-title">State what a finding should be measured against</h2>
          <p className="subtle">
            V1 records optional asset context but reports hazard evidence only. NimbusX suppresses all asset-risk verdicts until a published template-specific decision policy exists.
          </p>
          <div className="form-grid form-grid--three">
            <label htmlFor="asset-template">
              Asset template <span className="optional">optional</span>
              <select
                id="asset-template"
                value={form.assetTemplate}
                onChange={(event) => updateField("assetTemplate", event.target.value)}
              >
                <option value="">No asset template</option>
                <option value="facility">Facility</option>
                <option value="campus">Campus</option>
                <option value="real_estate">Real estate</option>
                <option value="infrastructure">Infrastructure</option>
              </select>
            </label>
            <label htmlFor="asset-exposure">
              Exposure <span className="optional">optional</span>
              <input
                id="asset-exposure"
                value={form.exposure}
                onChange={(event) => updateField("exposure", event.target.value)}
                placeholder="Describe exposed operations"
              />
            </label>
            <label htmlFor="asset-vulnerability">
              Vulnerability <span className="optional">optional</span>
              <input
                id="asset-vulnerability"
                value={form.vulnerability}
                onChange={(event) => updateField("vulnerability", event.target.value)}
                placeholder="Describe relevant weakness"
              />
            </label>
          </div>

          <fieldset>
            <legend>Optional hazard thresholds (SI units)</legend>
            <div className="form-grid form-grid--three">
              <label htmlFor="threshold-heat">
                Extreme heat (°C)
                <input
                  id="threshold-heat"
                  inputMode="decimal"
                  value={form.extremeHeat}
                  onChange={(event) => updateField("extremeHeat", event.target.value)}
                />
              </label>
              <label htmlFor="threshold-cold">
                Extreme cold (°C)
                <input
                  id="threshold-cold"
                  inputMode="decimal"
                  value={form.extremeCold}
                  onChange={(event) => updateField("extremeCold", event.target.value)}
                />
              </label>
              <label htmlFor="threshold-precipitation">
                Heavy precipitation (mm)
                <input
                  id="threshold-precipitation"
                  inputMode="decimal"
                  value={form.heavyPrecipitation}
                  onChange={(event) => updateField("heavyPrecipitation", event.target.value)}
                />
              </label>
              <label htmlFor="threshold-wind">
                Wind speed (m/s)
                <input
                  id="threshold-wind"
                  inputMode="decimal"
                  value={form.windSpeed}
                  onChange={(event) => updateField("windSpeed", event.target.value)}
                />
              </label>
              <label htmlFor="threshold-drought">
                Drought precipitation (mm)
                <input
                  id="threshold-drought"
                  inputMode="decimal"
                  value={form.droughtPrecipitation}
                  onChange={(event) => updateField("droughtPrecipitation", event.target.value)}
                />
              </label>
            </div>
          </fieldset>
        </section>

        {form.mode === "baseline" || form.mode === "scenario" ? (
          <section className="surface" aria-labelledby="baseline-title">
            <p className="eyebrow">4. Baseline</p>
            <h2 id="baseline-title">Historical comparison period</h2>
            <div className="form-grid">
              <label htmlFor="baseline-start">
                Start year
                <input
                  id="baseline-start"
                  inputMode="numeric"
                  value={form.baselineStart}
                  onChange={(event) => updateField("baselineStart", event.target.value)}
                  required
                />
              </label>
              <label htmlFor="baseline-end">
                End year
                <input
                  id="baseline-end"
                  inputMode="numeric"
                  value={form.baselineEnd}
                  onChange={(event) => updateField("baselineEnd", event.target.value)}
                  required
                />
              </label>
            </div>
          </section>
        ) : null}

        {form.mode === "scenario" ? (
          <section className="surface" aria-labelledby="scenario-title">
            <p className="eyebrow">5. Emissions scenarios</p>
            <h2 id="scenario-title">Show a range, not a single certainty</h2>
            <div className="checkbox-row" role="group" aria-label="Emissions scenarios">
              {(["ssp126", "ssp245", "ssp585"] as const).map((scenario) => (
                <label key={scenario} className="checkbox-card">
                  <input
                    type="checkbox"
                    checked={scenarios.includes(scenario)}
                    onChange={() => toggleScenario(scenario)}
                  />
                  <span>{scenario.toUpperCase()}</span>
                </label>
              ))}
            </div>
          </section>
        ) : null}

        {error ? <ErrorPanel error={error} /> : null}
        <div className="assessment-form__submit">
          <p className="subtle">
            Submitting queues an analysis that evaluates source evidence. It does not claim a result before
            providers and evidence records have been evaluated.
          </p>
          <button className="button button--primary button--large" type="submit" disabled={submitting}>
            {submitting ? "Queueing assessment…" : "Queue assessment"}
          </button>
        </div>
      </form>
    </>
  );
}
