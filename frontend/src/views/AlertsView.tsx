import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type {
  AlertEvaluationResult,
  AlertRule,
  AlertTriggerType,
  Analysis,
  HazardType,
  NotificationChannel,
  NotificationChannelKind,
  NotificationDeliveryMode,
  NotificationDispatchReceipt,
  PortfolioAsset,
  Severity
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
import { displayLikelihood, titleCase } from "../lib/format";
import { displayDateTime } from "../lib/time";

const hazards: HazardType[] = [
  "extreme_heat",
  "extreme_cold",
  "heavy_precipitation",
  "wind",
  "drought"
];

const triggerDescriptions: Record<AlertTriggerType, string> = {
  observed_threshold_breach:
    "Records an event when a completed assessment contains an observed threshold breach for the selected hazard.",
  baseline_likelihood:
    "Records an event when a source-backed historical likelihood meets the configured probability threshold.",
  severity_at_least:
    "Records an event when the returned hazard-finding severity meets or exceeds the configured review level."
};

interface RuleForm {
  name: string;
  assetId: string;
  hazard: HazardType;
  triggerType: AlertTriggerType;
  minimumLikelihood: string;
  minimumSeverity: Exclude<Severity, "unknown">;
  enabled: boolean;
}

function initialRuleForm(): RuleForm {
  return {
    name: "",
    assetId: "",
    hazard: "extreme_heat",
    triggerType: "observed_threshold_breach",
    minimumLikelihood: "0.2",
    minimumSeverity: "moderate",
    enabled: true
  };
}

interface NotificationForm {
  name: string;
  kind: NotificationChannelKind;
  target: string;
  deliveryMode: NotificationDeliveryMode;
  secretReference: string;
  enabled: boolean;
}

function initialNotificationForm(): NotificationForm {
  return {
    name: "",
    kind: "webhook",
    target: "",
    deliveryMode: "dry_run",
    secretReference: "",
    enabled: true
  };
}

function isTerminal(analysis: Analysis): boolean {
  return analysis.status === "complete" || analysis.status === "partial" || analysis.status === "failed" || analysis.status === "expired";
}

function EvidenceLinks(props: { analysisId: string; evidenceIds: string[]; navigate: (to: string) => void }) {
  if (props.evidenceIds.length === 0) {
    return <>No evidence IDs returned</>;
  }
  return (
    <RouteLink
      className="text-link"
      to={"/analyses/" + encodeURIComponent(props.analysisId) + "/evidence"}
      navigate={props.navigate}
    >
      {props.evidenceIds.length} evidence record{props.evidenceIds.length === 1 ? "" : "s"}
    </RouteLink>
  );
}

export function AlertsView(props: { projectId: string; navigate: (to: string) => void }) {
  const [rules, setRules] = useState<AlertRule[] | null>(null);
  const [events, setEvents] = useState<Awaited<ReturnType<typeof api.listAlertEvents>> | null>(null);
  const [channels, setChannels] = useState<NotificationChannel[] | null>(null);
  const [assets, setAssets] = useState<PortfolioAsset[] | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [form, setForm] = useState<RuleForm>(initialRuleForm);
  const [createError, setCreateError] = useState<unknown>(null);
  const [creating, setCreating] = useState(false);
  const [selectedAnalysisIds, setSelectedAnalysisIds] = useState<string[]>([]);
  const [evaluatingRuleId, setEvaluatingRuleId] = useState<string | null>(null);
  const [evaluationError, setEvaluationError] = useState<unknown>(null);
  const [evaluation, setEvaluation] = useState<AlertEvaluationResult | null>(null);
  const [notificationForm, setNotificationForm] = useState<NotificationForm>(initialNotificationForm);
  const [notificationError, setNotificationError] = useState<unknown>(null);
  const [creatingNotification, setCreatingNotification] = useState(false);
  const [selectedAlertEventId, setSelectedAlertEventId] = useState("");
  const [selectedChannelId, setSelectedChannelId] = useState("");
  const [receipts, setReceipts] = useState<NotificationDispatchReceipt[] | null>(null);
  const [receiptError, setReceiptError] = useState<unknown>(null);
  const [dispatching, setDispatching] = useState(false);

  const terminalAnalyses = useMemo(
    () => analyses?.filter(isTerminal) ?? [],
    [analyses]
  );

  const load = useCallback(async () => {
    setError(null);
    try {
      const [nextRules, nextEvents, nextChannels, nextAssets, nextAnalyses] = await Promise.all([
        api.listAlertRules(props.projectId),
        api.listAlertEvents(props.projectId),
        api.listNotificationChannels(props.projectId),
        api.listProjectAssets(props.projectId),
        api.listProjectAnalyses(props.projectId)
      ]);
      setRules(nextRules);
      setEvents(nextEvents);
      setChannels(nextChannels);
      setAssets(nextAssets);
      setAnalyses(nextAnalyses);
      setSelectedAlertEventId((current) =>
        nextEvents.some((alertEvent) => alertEvent.id === current) ? current : (nextEvents[0]?.id ?? "")
      );
      setSelectedChannelId((current) =>
        nextChannels.some((channel) => channel.id === current) ? current : (nextChannels[0]?.id ?? "")
      );
    } catch (requestError) {
      setError(requestError);
    }
  }, [props.projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  function updateForm<Key extends keyof RuleForm>(key: Key, value: RuleForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateNotificationForm<Key extends keyof NotificationForm>(
    key: Key,
    value: NotificationForm[Key]
  ) {
    setNotificationForm((current) => ({ ...current, [key]: value }));
  }

  async function createRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateError(null);
    if (!form.name.trim()) {
      setCreateError(new Error("Enter a descriptive alert rule name."));
      return;
    }

    let minimumLikelihood: number | undefined;
    if (form.triggerType === "baseline_likelihood") {
      minimumLikelihood = Number(form.minimumLikelihood);
      if (!Number.isFinite(minimumLikelihood) || minimumLikelihood < 0 || minimumLikelihood > 1) {
        setCreateError(new Error("Baseline likelihood must be a number from 0 to 1."));
        return;
      }
    }

    setCreating(true);
    try {
      const rule = await api.createAlertRule(props.projectId, {
        name: form.name.trim(),
        hazard: form.hazard,
        trigger_type: form.triggerType,
        asset_id: form.assetId.trim() || null,
        ...(minimumLikelihood === undefined ? {} : { minimum_likelihood: minimumLikelihood }),
        ...(form.triggerType === "severity_at_least" ? { minimum_severity: form.minimumSeverity } : {}),
        enabled: form.enabled
      });
      setRules((current) => [rule, ...(current ?? [])]);
      setForm(initialRuleForm());
    } catch (requestError) {
      setCreateError(requestError);
    } finally {
      setCreating(false);
    }
  }

  function toggleAnalysis(analysisId: string, checked: boolean) {
    setSelectedAnalysisIds((current) =>
      checked ? Array.from(new Set([...current, analysisId])) : current.filter((id) => id !== analysisId)
    );
  }

  async function evaluateRule(rule: AlertRule) {
    setEvaluationError(null);
    setEvaluation(null);
    if (selectedAnalysisIds.length === 0) {
      setEvaluationError(new Error("Select at least one terminal assessment before evaluating a rule."));
      return;
    }

    setEvaluatingRuleId(rule.id);
    try {
      const result = await api.evaluateAlertRule(props.projectId, rule.id, {
        analysis_ids: selectedAnalysisIds
      });
      setEvaluation(result);
      setEvents(await api.listAlertEvents(props.projectId));
    } catch (requestError) {
      setEvaluationError(requestError);
    } finally {
      setEvaluatingRuleId(null);
    }
  }

  async function createNotificationChannel(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotificationError(null);
    if (!notificationForm.name.trim() || !notificationForm.target.trim()) {
      setNotificationError(new Error("Enter a channel name and delivery target."));
      return;
    }
    setCreatingNotification(true);
    try {
      const channel = await api.createNotificationChannel(props.projectId, {
        name: notificationForm.name.trim(),
        kind: notificationForm.kind,
        target: notificationForm.target.trim(),
        delivery_mode: notificationForm.deliveryMode,
        enabled: notificationForm.enabled,
        secret_reference: notificationForm.secretReference.trim() || null
      });
      setChannels((current) => [channel, ...(current ?? [])]);
      setSelectedChannelId(channel.id);
      setNotificationForm(initialNotificationForm());
    } catch (requestError) {
      setNotificationError(requestError);
    } finally {
      setCreatingNotification(false);
    }
  }

  async function loadReceipts(eventId: string) {
    setReceiptError(null);
    if (!eventId) {
      setReceipts(null);
      return;
    }
    try {
      setReceipts(await api.listNotificationReceipts(props.projectId, eventId));
    } catch (requestError) {
      setReceiptError(requestError);
    }
  }

  async function dispatchSelectedEvent() {
    setReceiptError(null);
    if (!selectedAlertEventId || !selectedChannelId) {
      setReceiptError(new Error("Choose both a recorded event and a notification channel."));
      return;
    }
    setDispatching(true);
    try {
      const receipt = await api.dispatchAlertEvent(
        props.projectId,
        selectedAlertEventId,
        selectedChannelId
      );
      setReceipts((current) => [receipt, ...(current ?? [])]);
    } catch (requestError) {
      setReceiptError(requestError);
    } finally {
      setDispatching(false);
    }
  }

  const projectPath = "/projects/" + encodeURIComponent(props.projectId);

  return (
    <>
      <PageHeader
        eyebrow="Project workspace"
        title="Alert rules and recorded events"
        description="Alert rules evaluate completed, source-backed findings. NimbusX records evidence-linked events and can prepare safe dry-run delivery receipts; it never invents a future forecast or claims an unconfigured message was sent."
        actions={
          <RouteLink className="button button--secondary" to={projectPath} navigate={props.navigate}>
            Back to sites
          </RouteLink>
        }
      />
      <ProjectWorkspaceNav projectId={props.projectId} active="alerts" navigate={props.navigate} />

      {rules === null && events === null && !error ? <LoadingPanel label="Loading alert rules, event history, and terminal assessments..." /> : null}
      {error ? <ErrorPanel error={error} onRetry={() => void load()} /> : null}

      <div className="two-column two-column--wide-first">
        <section className="surface" aria-labelledby="alert-rule-title">
          <p className="eyebrow">Create an alert rule</p>
          <h2 id="alert-rule-title">Turn a defined finding into a review event</h2>
          <form className="stack-form" onSubmit={(event) => void createRule(event)} noValidate>
            <label htmlFor="alert-rule-name">
              Rule name
              <input
                id="alert-rule-name"
                value={form.name}
                onChange={(event) => updateForm("name", event.target.value)}
                maxLength={160}
                placeholder="e.g. Critical cooling assets: heat review"
                required
              />
            </label>
            <div className="form-grid form-grid--three">
              <label htmlFor="alert-rule-asset">
                Asset <span className="optional">optional</span>
                <select
                  id="alert-rule-asset"
                  value={form.assetId}
                  onChange={(event) => updateForm("assetId", event.target.value)}
                >
                  <option value="">Project-wide rule</option>
                  {assets?.map((asset) => (
                    <option value={asset.id} key={asset.id}>
                      {asset.name} ({titleCase(asset.criticality)})
                    </option>
                  ))}
                </select>
              </label>
              <label htmlFor="alert-rule-hazard">
                Hazard
                <select
                  id="alert-rule-hazard"
                  value={form.hazard}
                  onChange={(event) => updateForm("hazard", event.target.value as HazardType)}
                >
                  {hazards.map((hazard) => <option value={hazard} key={hazard}>{titleCase(hazard)}</option>)}
                </select>
              </label>
              <label htmlFor="alert-rule-trigger">
                Trigger type
                <select
                  id="alert-rule-trigger"
                  value={form.triggerType}
                  onChange={(event) => updateForm("triggerType", event.target.value as AlertTriggerType)}
                >
                  <option value="observed_threshold_breach">Observed threshold breach</option>
                  <option value="baseline_likelihood">Baseline likelihood</option>
                  <option value="severity_at_least">Finding severity</option>
                </select>
              </label>
            </div>
            <Notice tone="info" title="Trigger definition">
              <p>{triggerDescriptions[form.triggerType]}</p>
            </Notice>
            {form.triggerType === "baseline_likelihood" ? (
              <label htmlFor="alert-rule-likelihood">
                Minimum historical likelihood (0–1)
                <input
                  id="alert-rule-likelihood"
                  inputMode="decimal"
                  value={form.minimumLikelihood}
                  onChange={(event) => updateForm("minimumLikelihood", event.target.value)}
                  required
                />
                <span className="field-hint">For example, 0.2 means at least a 20% empirical likelihood.</span>
              </label>
            ) : null}
            {form.triggerType === "severity_at_least" ? (
              <label htmlFor="alert-rule-severity">
                Minimum finding severity
                <select
                  id="alert-rule-severity"
                  value={form.minimumSeverity}
                  onChange={(event) => updateForm("minimumSeverity", event.target.value as Exclude<Severity, "unknown">)}
                >
                  <option value="low">Low</option>
                  <option value="moderate">Moderate</option>
                  <option value="high">High</option>
                </select>
              </label>
            ) : null}
            <label className="checkbox-card" htmlFor="alert-rule-enabled">
              <input
                id="alert-rule-enabled"
                type="checkbox"
                checked={form.enabled}
                onChange={(event) => updateForm("enabled", event.target.checked)}
              />
              Enable this rule for manual evaluation
            </label>
            {createError ? <ErrorPanel error={createError} /> : null}
            <button className="button button--primary" type="submit" disabled={creating}>
              {creating ? "Saving rule..." : "Save alert rule"}
            </button>
          </form>
        </section>

        <aside className="surface surface--muted" aria-labelledby="alert-boundary-title">
          <p className="eyebrow">Delivery boundary</p>
          <h2 id="alert-boundary-title">No external delivery is hidden</h2>
          <ul className="text-list">
            <li>Rules can be project-wide or constrained to a registered asset.</li>
            <li>Evaluation retains an evidence reference for every recorded event.</li>
            <li>Notification channels create dry-run receipts by default; no external request is made.</li>
            <li>A selected live mode returns an explicit unavailable result until a reviewed dispatcher and audit store exist.</li>
          </ul>
        </aside>
      </div>

      <section className="surface" aria-labelledby="evaluation-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Manual evaluation</p>
            <h2 id="evaluation-title">Evaluate a rule against terminal assessments</h2>
          </div>
        </div>
        <p className="subtle">
          Choose completed, partial, failed, or expired assessments. The API records why a selection is skipped rather than treating missing evidence as a match.
        </p>
        {terminalAnalyses.length === 0 ? (
          <EmptyState title="No terminal project assessments are available">
            Create and complete a project-linked assessment before evaluating a rule.
          </EmptyState>
        ) : (
          <div className="checkbox-grid" role="group" aria-label="Terminal assessments to evaluate">
            {terminalAnalyses.map((analysis) => (
              <label className="checkbox-card checkbox-card--block" key={analysis.id}>
                <input
                  type="checkbox"
                  checked={selectedAnalysisIds.includes(analysis.id)}
                  onChange={(event) => toggleAnalysis(analysis.id, event.target.checked)}
                />
                <span>
                  <strong>{analysis.site.name}</strong>
                  <span className="table-detail">
                    {titleCase(analysis.resolved_mode ?? analysis.mode)} · {titleCase(analysis.status)} · {displayDateTime(analysis.created_at)}
                  </span>
                </span>
              </label>
            ))}
          </div>
        )}
        {evaluationError ? <ErrorPanel error={evaluationError} /> : null}
        {rules && rules.length === 0 ? (
          <EmptyState title="No alert rules have been saved">Create a rule before attempting an evaluation.</EmptyState>
        ) : null}
        {rules && rules.length > 0 ? (
          <div className="table-scroll evaluation-rule-table">
            <table>
              <caption>Project alert rules available for manual evaluation</caption>
              <thead>
                <tr>
                  <th scope="col">Rule</th>
                  <th scope="col">Condition</th>
                  <th scope="col">Scope</th>
                  <th scope="col">Status</th>
                  <th scope="col">Evaluate</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <th scope="row">{rule.name}</th>
                    <td>
                      {titleCase(rule.trigger_type)}
                      {rule.minimum_likelihood !== null ? <span className="table-detail">At least {displayLikelihood(rule.minimum_likelihood)}</span> : null}
                      {rule.minimum_severity ? <span className="table-detail">At least {titleCase(rule.minimum_severity)}</span> : null}
                    </td>
                    <td>{rule.asset_id ? <code>{rule.asset_id}</code> : "Project-wide"}</td>
                    <td>{rule.enabled ? "Enabled" : "Disabled"}</td>
                    <td>
                      <button
                        className="button button--secondary"
                        type="button"
                        disabled={!rule.enabled || evaluatingRuleId !== null || selectedAnalysisIds.length === 0}
                        onClick={() => void evaluateRule(rule)}
                      >
                        {evaluatingRuleId === rule.id ? "Evaluating..." : "Evaluate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {evaluation ? <EvaluationResult result={evaluation} navigate={props.navigate} /> : null}

      <section className="surface" aria-labelledby="alert-event-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Recorded event history</p>
            <h2 id="alert-event-title">Evidence-linked events</h2>
          </div>
          <button className="button button--secondary" type="button" onClick={() => void load()}>
            Refresh
          </button>
        </div>
        {events && events.length === 0 ? (
          <EmptyState title="No alert events have been recorded">
            Events appear only after a rule is manually evaluated against an assessment finding.
          </EmptyState>
        ) : null}
        {events && events.length > 0 ? (
          <div className="table-scroll">
            <table>
              <caption>Evidence-linked alert events recorded for this project</caption>
              <thead>
                <tr>
                  <th scope="col">Event</th>
                  <th scope="col">Hazard / kind</th>
                  <th scope="col">Assessment evidence</th>
                  <th scope="col">Delivery</th>
                  <th scope="col">Recorded</th>
                </tr>
              </thead>
              <tbody>
                {events.map((alertEvent) => (
                  <tr key={alertEvent.id}>
                    <th scope="row">
                      {alertEvent.summary}
                      {alertEvent.asset_id ? <span className="table-detail">Asset: {alertEvent.asset_id}</span> : null}
                    </th>
                    <td>{titleCase(alertEvent.hazard)}<span className="table-detail">{titleCase(alertEvent.event_kind)}</span></td>
                    <td><EvidenceLinks analysisId={alertEvent.analysis_id} evidenceIds={alertEvent.evidence_ids} navigate={props.navigate} /></td>
                    <td>{titleCase(alertEvent.delivery_status)}</td>
                    <td>{displayDateTime(alertEvent.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="surface" aria-labelledby="notification-channel-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Notification channels</p>
            <h2 id="notification-channel-title">Prepare a reviewed delivery target</h2>
          </div>
        </div>
        <div className="two-column two-column--wide-first">
          <form className="stack-form" onSubmit={(event) => void createNotificationChannel(event)} noValidate>
            <label htmlFor="notification-channel-name">
              Channel name
              <input
                id="notification-channel-name"
                value={notificationForm.name}
                onChange={(event) => updateNotificationForm("name", event.target.value)}
                placeholder="e.g. Facilities review webhook"
                maxLength={200}
                required
              />
            </label>
            <div className="form-grid form-grid--three">
              <label htmlFor="notification-channel-kind">
                Channel type
                <select
                  id="notification-channel-kind"
                  value={notificationForm.kind}
                  onChange={(event) => updateNotificationForm("kind", event.target.value as NotificationChannelKind)}
                >
                  <option value="webhook">HTTPS webhook</option>
                  <option value="email">Email recipient</option>
                  <option value="slack">Slack-compatible HTTPS webhook</option>
                </select>
              </label>
              <label htmlFor="notification-delivery-mode">
                Delivery mode
                <select
                  id="notification-delivery-mode"
                  value={notificationForm.deliveryMode}
                  onChange={(event) => updateNotificationForm("deliveryMode", event.target.value as NotificationDeliveryMode)}
                >
                  <option value="dry_run">Dry run only</option>
                  <option value="live">Live (currently unavailable)</option>
                </select>
              </label>
              <label className="checkbox-card" htmlFor="notification-channel-enabled">
                <input
                  id="notification-channel-enabled"
                  type="checkbox"
                  checked={notificationForm.enabled}
                  onChange={(event) => updateNotificationForm("enabled", event.target.checked)}
                />
                Enable this channel
              </label>
            </div>
            <label htmlFor="notification-channel-target">
              {notificationForm.kind === "email" ? "Recipient email" : "HTTPS target URL"}
              <input
                id="notification-channel-target"
                type={notificationForm.kind === "email" ? "email" : "url"}
                value={notificationForm.target}
                onChange={(event) => updateNotificationForm("target", event.target.value)}
                placeholder={notificationForm.kind === "email" ? "facilities@example.com" : "https://alerts.example.com/nimbusx"}
                required
              />
              <span className="field-hint">Webhooks and Slack-compatible targets must use HTTPS.</span>
            </label>
            <label htmlFor="notification-secret-reference">
              Secret-manager reference <span className="optional">optional</span>
              <input
                id="notification-secret-reference"
                value={notificationForm.secretReference}
                onChange={(event) => updateNotificationForm("secretReference", event.target.value)}
                placeholder="secret://tenant/operations-webhook"
              />
              <span className="field-hint">Only a <code>secret://</code> reference is accepted. It is never returned to the browser after creation.</span>
            </label>
            {notificationError ? <ErrorPanel error={notificationError} /> : null}
            <button className="button button--primary" type="submit" disabled={creatingNotification}>
              {creatingNotification ? "Saving channel..." : "Save notification channel"}
            </button>
          </form>
          <aside className="surface surface--muted" aria-labelledby="notification-boundary-title">
            <p className="eyebrow">Safety control</p>
            <h3 id="notification-boundary-title">Nothing is sent from this page</h3>
            <ul className="text-list">
              <li>A dry run records the small event envelope and makes no network request.</li>
              <li>Live delivery stays unavailable until a durable dispatcher, retry queue, secret manager, and delivery audit path are reviewed.</li>
              <li>Secret references are intentionally not shown after channel creation.</li>
            </ul>
          </aside>
        </div>

        {channels && channels.length === 0 ? (
          <EmptyState title="No notification channels are configured">
            Add a reviewed target if you want to exercise the evidence-linked delivery flow safely.
          </EmptyState>
        ) : null}
        {channels && channels.length > 0 ? (
          <div className="table-scroll">
            <table>
              <caption>Project notification channels</caption>
              <thead>
                <tr>
                  <th scope="col">Channel</th>
                  <th scope="col">Target</th>
                  <th scope="col">Mode</th>
                  <th scope="col">Secret reference</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((channel) => (
                  <tr key={channel.id}>
                    <th scope="row">
                      {channel.name}
                      <span className="table-detail">{titleCase(channel.kind)} {channel.enabled ? "enabled" : "disabled"}</span>
                    </th>
                    <td className="wrap-anywhere">{channel.target}</td>
                    <td>{titleCase(channel.delivery_mode)}</td>
                    <td>{channel.has_secret_reference ? "Configured (not displayed)" : "None"}</td>
                    <td>{displayDateTime(channel.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="surface" aria-labelledby="notification-dispatch-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Delivery rehearsal</p>
            <h2 id="notification-dispatch-title">Record a safe notification receipt</h2>
          </div>
        </div>
        <p className="subtle">
          Choose an existing evidence-linked event and a configured channel. Dry run is the default. A live-mode channel will return an explicit unavailable receipt instead of claiming an external message was sent.
        </p>
        <div className="form-grid">
          <label htmlFor="notification-event-select">
            Recorded event
            <select
              id="notification-event-select"
              value={selectedAlertEventId}
              onChange={(event) => {
                const eventId = event.target.value;
                setSelectedAlertEventId(eventId);
                void loadReceipts(eventId);
              }}
              disabled={!events || events.length === 0}
            >
              <option value="">Choose an event</option>
              {events?.map((alertEvent) => (
                <option key={alertEvent.id} value={alertEvent.id}>
                  {titleCase(alertEvent.hazard)}: {alertEvent.summary.slice(0, 80)}
                </option>
              ))}
            </select>
          </label>
          <label htmlFor="notification-channel-select">
            Notification channel
            <select
              id="notification-channel-select"
              value={selectedChannelId}
              onChange={(event) => setSelectedChannelId(event.target.value)}
              disabled={!channels || channels.length === 0}
            >
              <option value="">Choose a channel</option>
              {channels?.map((channel) => (
                <option key={channel.id} value={channel.id}>
                  {channel.name} ({titleCase(channel.delivery_mode)})
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="button-row">
          <button
            className="button button--primary"
            type="button"
            disabled={dispatching || !selectedAlertEventId || !selectedChannelId}
            onClick={() => void dispatchSelectedEvent()}
          >
            {dispatching ? "Recording receipt..." : "Record delivery receipt"}
          </button>
          <button
            className="button button--secondary"
            type="button"
            disabled={!selectedAlertEventId}
            onClick={() => void loadReceipts(selectedAlertEventId)}
          >
            Load receipts
          </button>
        </div>
        {receiptError ? <ErrorPanel error={receiptError} /> : null}
        {receipts && receipts.length === 0 ? (
          <EmptyState title="No delivery receipts for this event">
            A receipt appears only after you intentionally run the safe dispatch action above.
          </EmptyState>
        ) : null}
        {receipts && receipts.length > 0 ? (
          <div className="table-scroll">
            <table>
              <caption>Notification receipts for the selected alert event</caption>
              <thead>
                <tr>
                  <th scope="col">Status</th>
                  <th scope="col">Message</th>
                  <th scope="col">Evidence IDs</th>
                  <th scope="col">Recorded</th>
                </tr>
              </thead>
              <tbody>
                {receipts.map((receipt) => (
                  <tr key={receipt.id}>
                    <th scope="row">{titleCase(receipt.status)}</th>
                    <td>{receipt.message}</td>
                    <td>{renderEvidenceIdCount(receipt.payload)}</td>
                    <td>{displayDateTime(receipt.created_at)}</td>
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

function renderEvidenceIdCount(payload: Record<string, unknown>): string {
  const evidenceIds = payload.evidence_ids;
  if (!Array.isArray(evidenceIds) || !evidenceIds.every((value) => typeof value === "string")) {
    return "No evidence IDs in receipt payload";
  }
  return evidenceIds.length + " evidence ID" + (evidenceIds.length === 1 ? "" : "s");
}

function EvaluationResult(props: { result: AlertEvaluationResult; navigate: (to: string) => void }) {
  const { result } = props;
  return (
    <section className="surface evaluation-result" aria-labelledby="evaluation-result-title">
      <p className="eyebrow">Evaluation result</p>
      <h2 id="evaluation-result-title">{result.rule.name}</h2>
      <div className="definition-list">
        <div>
          <dt>New events</dt>
          <dd>{result.created_count}</dd>
        </div>
        <div>
          <dt>Existing events</dt>
          <dd>{result.existing_count}</dd>
        </div>
        <div>
          <dt>Skipped assessments</dt>
          <dd>{result.skipped.length}</dd>
        </div>
      </div>
      {result.events.length > 0 ? (
        <ul className="source-list">
          {result.events.map((event) => (
            <li key={event.id}>
              <strong>{event.summary}</strong>
              <span>{titleCase(event.hazard)} · {titleCase(event.event_kind)}</span>
              <EvidenceLinks analysisId={event.analysis_id} evidenceIds={event.evidence_ids} navigate={props.navigate} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="subtle">No new or existing event record was returned for this evaluation.</p>
      )}
      {result.skipped.length > 0 ? (
        <Notice tone="warning" title="Skipped assessments">
          <ul className="text-list">
            {result.skipped.map((skip) => <li key={skip.analysis_id}>{skip.analysis_id}: {skip.reason}</li>)}
          </ul>
        </Notice>
      ) : null}
      {result.limitations.length > 0 ? (
        <Notice tone="warning" title="Evaluation limitations">
          <ul className="text-list">
            {result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
          </ul>
        </Notice>
      ) : null}
    </section>
  );
}
