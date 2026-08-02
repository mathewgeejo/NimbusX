import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type {
  AssetCriticality,
  AssetImportResult,
  AssetTemplate,
  AssetTemplateField,
  GeoJsonFeatureCollection,
  PortfolioAsset
} from "../api/contracts";
import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  Notice,
  PageHeader,
  RouteLink
} from "../components/ui";
import { ProjectWorkspaceNav } from "../components/workspaceNavigation";
import { titleCase } from "../lib/format";
import { displayDateTime } from "../lib/time";

type ImportKind = "csv" | "geojson";

interface AssetForm {
  name: string;
  siteId: string;
  templateId: string;
  externalId: string;
  criticality: AssetCriticality;
  tags: string;
  exposure: Record<string, string>;
  vulnerability: Record<string, string>;
}

function initialAssetForm(): AssetForm {
  return {
    name: "",
    siteId: "",
    templateId: "",
    externalId: "",
    criticality: "medium",
    tags: "",
    exposure: {},
    vulnerability: {}
  };
}

function parseTags(value: string): string[] {
  return Array.from(new Set(value.split(",").map((tag) => tag.trim()).filter(Boolean)));
}

function parseFieldValue(value: string, field: AssetTemplateField): unknown {
  const normalized = value.trim();
  if (field.value_type === "number") {
    const parsed = Number(normalized);
    if (!Number.isFinite(parsed)) {
      throw new Error(field.label + " must be a number.");
    }
    return parsed;
  }
  if (field.value_type === "boolean") {
    if (normalized !== "true" && normalized !== "false") {
      throw new Error(field.label + " must be true or false.");
    }
    return normalized === "true";
  }
  return normalized;
}

function buildAttributes(
  fields: AssetTemplateField[],
  values: Record<string, string>,
  groupName: string
): Record<string, unknown> {
  const attributes: Record<string, unknown> = {};
  for (const field of fields) {
    const value = values[field.key] ?? "";
    if (field.required && !value.trim()) {
      throw new Error("Enter " + field.label + " in the " + groupName + " fields.");
    }
    if (value.trim()) {
      attributes[field.key] = parseFieldValue(value, field);
    }
  }
  return attributes;
}

function inputType(field: AssetTemplateField): "text" | "number" {
  return field.value_type === "number" ? "number" : "text";
}

function ImportResultPanel(props: { result: AssetImportResult }) {
  const { result } = props;
  return (
    <section className="surface import-result" aria-labelledby="import-result-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Import result</p>
          <h2 id="import-result-title">{titleCase(result.status)} import</h2>
        </div>
        <span className={"status-pill status-pill--" + (result.status === "complete" ? "complete" : result.status === "failed" ? "failed" : "partial")}>
          {result.dry_run ? "Validation only" : "Applied"}
        </span>
      </div>
      <div className="definition-list">
        <div>
          <dt>Created</dt>
          <dd>{result.created_count}</dd>
        </div>
        <div>
          <dt>Rejected</dt>
          <dd>{result.rejected_count}</dd>
        </div>
        <div>
          <dt>Rows checked</dt>
          <dd>{result.rows.length}</dd>
        </div>
      </div>
      <div className="table-scroll">
        <table>
          <caption>Asset import row outcomes</caption>
          <thead>
            <tr>
              <th scope="col">Row</th>
              <th scope="col">Name</th>
              <th scope="col">Status</th>
              <th scope="col">Result</th>
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row) => (
              <tr key={row.row_number + "-" + (row.asset_id ?? row.code ?? row.name ?? "row")}>
                <th scope="row">{row.row_number}</th>
                <td>{row.name ?? "Not supplied"}</td>
                <td>{titleCase(row.status)}</td>
                <td>
                  {row.message ?? "No row message returned."}
                  {row.code ? <span className="table-detail">Code: {row.code}</span> : null}
                  {row.asset_id ? <span className="table-detail">Asset: {row.asset_id}</span> : null}
                  {row.site_id ? <span className="table-detail">Site: {row.site_id}</span> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {result.limitations.length > 0 ? (
        <Notice tone="warning" title="Import limitations">
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

export function AssetInventoryView(props: { projectId: string; navigate: (to: string) => void }) {
  const [assets, setAssets] = useState<PortfolioAsset[] | null>(null);
  const [templates, setTemplates] = useState<AssetTemplate[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [assetForm, setAssetForm] = useState<AssetForm>(initialAssetForm);
  const [createError, setCreateError] = useState<unknown>(null);
  const [creating, setCreating] = useState(false);
  const [importKind, setImportKind] = useState<ImportKind>("csv");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importTemplateId, setImportTemplateId] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<unknown>(null);
  const [importResult, setImportResult] = useState<AssetImportResult | null>(null);

  const selectedTemplate = useMemo(
    () => templates?.find((template) => template.id === assetForm.templateId) ?? null,
    [assetForm.templateId, templates]
  );

  const load = useCallback(async () => {
    setError(null);
    try {
      const [nextTemplates, nextAssets] = await Promise.all([
        api.listAssetTemplates(),
        api.listProjectAssets(props.projectId)
      ]);
      setTemplates(nextTemplates);
      setAssets(nextAssets);
      if (nextTemplates.length > 0) {
        setAssetForm((current) =>
          current.templateId ? current : { ...current, templateId: nextTemplates[0].id }
        );
        setImportTemplateId((current) => current || nextTemplates[0].id);
      }
    } catch (requestError) {
      setError(requestError);
    }
  }, [props.projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  function updateAssetForm<Key extends keyof AssetForm>(key: Key, value: AssetForm[Key]) {
    setAssetForm((current) => ({ ...current, [key]: value }));
  }

  function updateAttribute(kind: "exposure" | "vulnerability", fieldKey: string, value: string) {
    setAssetForm((current) => ({
      ...current,
      [kind]: { ...current[kind], [fieldKey]: value }
    }));
  }

  async function createAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateError(null);
    if (!selectedTemplate) {
      setCreateError(new Error("Choose an asset template before saving an asset."));
      return;
    }
    if (!assetForm.name.trim() || !assetForm.siteId.trim()) {
      setCreateError(new Error("Enter both an asset name and an existing point-site ID."));
      return;
    }

    let exposure: Record<string, unknown>;
    let vulnerability: Record<string, unknown>;
    try {
      exposure = buildAttributes(
        selectedTemplate.required_exposure_fields,
        assetForm.exposure,
        "exposure"
      );
      vulnerability = buildAttributes(
        selectedTemplate.required_vulnerability_fields,
        assetForm.vulnerability,
        "vulnerability"
      );
    } catch (validationError) {
      setCreateError(validationError);
      return;
    }

    setCreating(true);
    try {
      const asset = await api.createProjectAsset(props.projectId, {
        name: assetForm.name.trim(),
        site_id: assetForm.siteId.trim(),
        template_id: selectedTemplate.id,
        external_id: assetForm.externalId.trim() || null,
        criticality: assetForm.criticality,
        tags: parseTags(assetForm.tags),
        exposure,
        vulnerability
      });
      setAssets((current) => [asset, ...(current ?? [])]);
      setAssetForm({ ...initialAssetForm(), templateId: selectedTemplate.id });
    } catch (requestError) {
      setCreateError(requestError);
    } finally {
      setCreating(false);
    }
  }

  async function importAssets(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setImportError(null);
    setImportResult(null);
    if (!importFile) {
      setImportError(new Error("Choose a " + (importKind === "csv" ? "CSV" : "GeoJSON") + " file first."));
      return;
    }

    let payload: { csv_text?: string; geojson?: GeoJsonFeatureCollection; default_template_id?: string; dry_run: boolean };
    try {
      const text = await importFile.text();
      if (!text.trim()) {
        throw new Error("The selected import file is empty.");
      }
      payload = { dry_run: dryRun };
      if (importTemplateId) {
        payload.default_template_id = importTemplateId;
      }
      if (importKind === "csv") {
        payload.csv_text = text;
      } else {
        const parsed: unknown = JSON.parse(text);
        if (
          typeof parsed !== "object" ||
          parsed === null ||
          Array.isArray(parsed) ||
          (parsed as { type?: unknown }).type !== "FeatureCollection" ||
          !Array.isArray((parsed as { features?: unknown }).features)
        ) {
          throw new Error("GeoJSON imports must contain a FeatureCollection.");
        }
        payload.geojson = parsed as GeoJsonFeatureCollection;
      }
    } catch (validationError) {
      setImportError(validationError);
      return;
    }

    setImporting(true);
    try {
      const result = await api.importProjectAssets(props.projectId, payload);
      setImportResult(result);
      if (!result.dry_run && result.created_count > 0) {
        setAssets(await api.listProjectAssets(props.projectId));
      }
    } catch (requestError) {
      setImportError(requestError);
    } finally {
      setImporting(false);
    }
  }

  const projectPath = "/projects/" + encodeURIComponent(props.projectId);

  return (
    <>
      <PageHeader
        eyebrow="Project workspace"
        title="Asset inventory and import"
        description="Connect a real asset to a point site, capture the exposure and vulnerability fields required by its template, and preserve per-row import outcomes."
        actions={
          <RouteLink className="button button--secondary" to={projectPath} navigate={props.navigate}>
            Back to sites
          </RouteLink>
        }
      />
      <ProjectWorkspaceNav projectId={props.projectId} active="assets" navigate={props.navigate} />

      {assets === null && templates === null && !error ? <LoadingPanel label="Loading asset templates and inventory..." /> : null}
      {error ? <ErrorPanel error={error} onRetry={() => void load()} /> : null}

      {templates ? (
        <section className="surface" aria-labelledby="asset-templates-title">
          <p className="eyebrow">Asset templates</p>
          <h2 id="asset-templates-title">Required context before an asset is assessed</h2>
          {templates.length === 0 ? (
            <EmptyState title="No asset templates are available">
              NimbusX cannot create an asset without a versioned template and its declared evidence fields.
            </EmptyState>
          ) : (
            <div className="template-grid">
              {templates.map((template) => (
                <article className="template-card" key={template.id}>
                  <div className="section-heading">
                    <div>
                      <h3>{template.display_name}</h3>
                      <p className="table-detail">Template version {template.version}</p>
                    </div>
                  </div>
                  <p>{template.description}</p>
                  <dl className="compact-definition-list">
                    <div>
                      <dt>Exposure fields</dt>
                      <dd>{template.required_exposure_fields.length}</dd>
                    </div>
                    <div>
                      <dt>Vulnerability fields</dt>
                      <dd>{template.required_vulnerability_fields.length}</dd>
                    </div>
                    <div>
                      <dt>Hazards</dt>
                      <dd>{template.supported_hazards.map(titleCase).join(", ") || "None declared"}</dd>
                    </div>
                  </dl>
                  {template.operational_rules.length > 0 ? (
                    <details>
                      <summary>{template.operational_rules.length} template control{template.operational_rules.length === 1 ? "" : "s"}</summary>
                      <ul className="text-list">
                        {template.operational_rules.map((rule) => (
                          <li key={rule.id}>
                            <strong>{rule.name}:</strong> {rule.action}
                            <span className="table-detail">{rule.rationale}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      <div className="two-column two-column--wide-first asset-workspace-grid">
        <section className="surface" aria-labelledby="create-asset-title">
          <p className="eyebrow">Register an asset</p>
          <h2 id="create-asset-title">Link an asset to a saved point site</h2>
          <form className="stack-form" onSubmit={(event) => void createAsset(event)} noValidate>
            <div className="form-grid">
              <label htmlFor="asset-name">
                Asset name
                <input
                  id="asset-name"
                  value={assetForm.name}
                  onChange={(event) => updateAssetForm("name", event.target.value)}
                  maxLength={160}
                  required
                />
              </label>
              <label htmlFor="asset-site-id">
                Point site ID
                <input
                  id="asset-site-id"
                  value={assetForm.siteId}
                  onChange={(event) => updateAssetForm("siteId", event.target.value)}
                  placeholder="Saved site UUID"
                  required
                />
                <span className="field-hint">Create the point site from the Sites & assessments tab first.</span>
              </label>
            </div>
            <div className="form-grid form-grid--three">
              <label htmlFor="asset-template-select">
                Asset template
                <select
                  id="asset-template-select"
                  value={assetForm.templateId}
                  onChange={(event) => updateAssetForm("templateId", event.target.value)}
                  disabled={!templates || templates.length === 0}
                  required
                >
                  <option value="">Choose a template</option>
                  {templates?.map((template) => (
                    <option value={template.id} key={template.id}>
                      {template.display_name} ({template.version})
                    </option>
                  ))}
                </select>
              </label>
              <label htmlFor="asset-criticality">
                Criticality
                <select
                  id="asset-criticality"
                  value={assetForm.criticality}
                  onChange={(event) => updateAssetForm("criticality", event.target.value as AssetCriticality)}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </label>
              <label htmlFor="asset-external-id">
                External asset ID <span className="optional">optional</span>
                <input
                  id="asset-external-id"
                  value={assetForm.externalId}
                  onChange={(event) => updateAssetForm("externalId", event.target.value)}
                  maxLength={160}
                />
              </label>
            </div>
            <label htmlFor="asset-tags">
              Tags <span className="optional">optional</span>
              <input
                id="asset-tags"
                value={assetForm.tags}
                onChange={(event) => updateAssetForm("tags", event.target.value)}
                placeholder="e.g. critical-load, leased, cooling"
              />
              <span className="field-hint">Separate tags with commas. Duplicates are removed before saving.</span>
            </label>

            {selectedTemplate ? (
              <TemplateAttributes
                template={selectedTemplate}
                exposure={assetForm.exposure}
                vulnerability={assetForm.vulnerability}
                onChange={updateAttribute}
              />
            ) : null}

            {createError ? <ErrorPanel error={createError} /> : null}
            <button className="button button--primary" type="submit" disabled={creating || !selectedTemplate}>
              {creating ? "Saving asset..." : "Save asset"}
            </button>
          </form>
        </section>

        <aside className="surface surface--muted" aria-labelledby="asset-boundaries-title">
          <p className="eyebrow">Inventory boundaries</p>
          <h2 id="asset-boundaries-title">Evidence, not a risk verdict</h2>
          <ul className="text-list">
            <li>Each asset must reference a saved point site and a versioned template.</li>
            <li>Template fields make the context inspectable; they do not by themselves create a risk decision.</li>
            <li>Flood, wildfire, and building-level exposure are not inferred from a site coordinate.</li>
          </ul>
        </aside>
      </div>

      <section className="surface" aria-labelledby="asset-list-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Registered assets</p>
            <h2 id="asset-list-title">Project asset register</h2>
          </div>
          <button className="button button--secondary" type="button" onClick={() => void load()}>
            Refresh
          </button>
        </div>
        {assets && assets.length === 0 ? (
          <EmptyState title="No assets have been registered">
            Register an individual asset or validate a CSV or point GeoJSON import below.
          </EmptyState>
        ) : null}
        {assets && assets.length > 0 ? (
          <div className="table-scroll">
            <table>
              <caption>Assets registered to this project</caption>
              <thead>
                <tr>
                  <th scope="col">Asset</th>
                  <th scope="col">Criticality</th>
                  <th scope="col">Point site</th>
                  <th scope="col">Template</th>
                  <th scope="col">Context</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <tr key={asset.id}>
                    <th scope="row">
                      {asset.name}
                      {asset.external_id ? <span className="table-detail">External ID: {asset.external_id}</span> : null}
                    </th>
                    <td>{titleCase(asset.criticality)}</td>
                    <td><code>{asset.site_id}</code></td>
                    <td><code>{asset.template_id}</code></td>
                    <td>
                      {asset.tags.length > 0 ? asset.tags.join(", ") : "No tags"}
                      <span className="table-detail">
                        {Object.keys(asset.exposure).length} exposure / {Object.keys(asset.vulnerability).length} vulnerability fields
                      </span>
                    </td>
                    <td>{displayDateTime(asset.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="surface" aria-labelledby="asset-import-title">
        <p className="eyebrow">Bulk import</p>
        <h2 id="asset-import-title">Validate before you create assets</h2>
        <p className="subtle">
          Upload CSV text or point-only GeoJSON. Start with validation only; rows are reported individually and rejected geometry is not silently changed.
        </p>
        <form className="stack-form" onSubmit={(event) => void importAssets(event)} noValidate>
          <fieldset>
            <legend>Import source</legend>
            <div className="checkbox-row" role="radiogroup" aria-label="Import source type">
              <label className="checkbox-card">
                <input
                  type="radio"
                  name="asset-import-kind"
                  checked={importKind === "csv"}
                  onChange={() => setImportKind("csv")}
                />
                CSV
              </label>
              <label className="checkbox-card">
                <input
                  type="radio"
                  name="asset-import-kind"
                  checked={importKind === "geojson"}
                  onChange={() => setImportKind("geojson")}
                />
                GeoJSON FeatureCollection
              </label>
            </div>
          </fieldset>
          <div className="form-grid">
            <label htmlFor="asset-import-file">
              {importKind === "csv" ? "CSV file" : "GeoJSON file"}
              <input
                id="asset-import-file"
                type="file"
                accept={importKind === "csv" ? ".csv,text/csv" : ".geojson,.json,application/geo+json,application/json"}
                onChange={(event) => setImportFile(event.target.files?.[0] ?? null)}
                required
              />
            </label>
            <label htmlFor="asset-import-template">
              Default asset template <span className="optional">optional</span>
              <select
                id="asset-import-template"
                value={importTemplateId}
                onChange={(event) => setImportTemplateId(event.target.value)}
              >
                <option value="">Use each row&apos;s template ID</option>
                {templates?.map((template) => (
                  <option value={template.id} key={template.id}>{template.display_name}</option>
                ))}
              </select>
            </label>
          </div>
          <label className="checkbox-card" htmlFor="asset-import-dry-run">
            <input
              id="asset-import-dry-run"
              type="checkbox"
              checked={dryRun}
              onChange={(event) => setDryRun(event.target.checked)}
            />
            Validate only — do not create assets yet
          </label>
          {importError ? <ErrorPanel error={importError} /> : null}
          <button className="button button--primary" type="submit" disabled={importing}>
            {importing ? "Processing import..." : dryRun ? "Validate import" : "Create imported assets"}
          </button>
        </form>
      </section>

      {importResult ? <ImportResultPanel result={importResult} /> : null}
    </>
  );
}

function TemplateAttributes(props: {
  template: AssetTemplate;
  exposure: Record<string, string>;
  vulnerability: Record<string, string>;
  onChange: (kind: "exposure" | "vulnerability", fieldKey: string, value: string) => void;
}) {
  const groups: Array<{
    key: "exposure" | "vulnerability";
    title: string;
    fields: AssetTemplateField[];
    values: Record<string, string>;
  }> = [
    {
      key: "exposure",
      title: "Exposure context",
      fields: props.template.required_exposure_fields,
      values: props.exposure
    },
    {
      key: "vulnerability",
      title: "Vulnerability context",
      fields: props.template.required_vulnerability_fields,
      values: props.vulnerability
    }
  ];

  return (
    <div className="template-attribute-groups">
      {groups.map((group) => (
        <fieldset key={group.key}>
          <legend>{group.title}</legend>
          {group.fields.length === 0 ? (
            <p className="subtle">This template declares no {group.key} fields.</p>
          ) : (
            <div className="form-grid">
              {group.fields.map((field) => (
                <label key={field.key} htmlFor={group.key + "-" + field.key}>
                  {field.label} {field.required ? null : <span className="optional">optional</span>}
                  {field.allowed_values.length > 0 ? (
                    <select
                      id={group.key + "-" + field.key}
                      value={group.values[field.key] ?? ""}
                      onChange={(event) => props.onChange(group.key, field.key, event.target.value)}
                      required={field.required}
                    >
                      <option value="">Choose a value</option>
                      {field.allowed_values.map((value) => (
                        <option value={value} key={value}>{value}</option>
                      ))}
                    </select>
                  ) : field.value_type === "boolean" ? (
                    <select
                      id={group.key + "-" + field.key}
                      value={group.values[field.key] ?? ""}
                      onChange={(event) => props.onChange(group.key, field.key, event.target.value)}
                      required={field.required}
                    >
                      <option value="">Choose a value</option>
                      <option value="true">True</option>
                      <option value="false">False</option>
                    </select>
                  ) : (
                    <input
                      id={group.key + "-" + field.key}
                      type={inputType(field)}
                      value={group.values[field.key] ?? ""}
                      onChange={(event) => props.onChange(group.key, field.key, event.target.value)}
                      required={field.required}
                    />
                  )}
                  <span className="field-hint">{field.description}</span>
                </label>
              ))}
            </div>
          )}
        </fieldset>
      ))}
    </div>
  );
}
