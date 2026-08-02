import { useEffect, useRef } from "react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import type { AnalysisDecision, AnalysisStatus, Decision } from "../api/contracts";
import { titleCase } from "../lib/format";

export function RouteLink(
  props: AnchorHTMLAttributes<HTMLAnchorElement> & {
    to: string;
    navigate: (to: string) => void;
  }
) {
  const { to, navigate, onClick, children, ...anchorProps } = props;

  return (
    <a
      {...anchorProps}
      href={to}
      onClick={(event) => {
        onClick?.(event);
        if (
          !event.defaultPrevented &&
          event.button === 0 &&
          !event.metaKey &&
          !event.ctrlKey &&
          !event.shiftKey &&
          !event.altKey
        ) {
          event.preventDefault();
          navigate(to);
        }
      }}
    >
      {children}
    </a>
  );
}

export function WorkspaceShell(props: {
  pathname: string;
  navigate: (to: string) => void;
  children: ReactNode;
}) {
  const { pathname, navigate, children } = props;
  const mainRef = useRef<HTMLElement>(null);
  const previousPathname = useRef(pathname);
  const isCurrent = (target: string) =>
    target === "/" ? pathname === "/" || pathname === "/portfolio" : pathname.startsWith(target);

  useEffect(() => {
    if (previousPathname.current !== pathname) {
      mainRef.current?.focus({ preventScroll: true });
    }
    previousPathname.current = pathname;
  }, [pathname]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="topbar">
        <div className="topbar__inner">
          <RouteLink className="brand" to="/portfolio" navigate={navigate} aria-label="NimbusX portfolio">
            <span className="brand__mark" aria-hidden="true">
              N
            </span>
            <span>
              <strong>NimbusX</strong>
              <small>Climate risk evidence workspace</small>
            </span>
          </RouteLink>
          <nav className="primary-nav" aria-label="Primary navigation">
            <RouteLink
              className={isCurrent("/portfolio") || isCurrent("/") ? "nav-link nav-link--active" : "nav-link"}
              to="/portfolio"
              navigate={navigate}
              aria-current={isCurrent("/portfolio") || isCurrent("/") ? "page" : undefined}
            >
              Portfolio
            </RouteLink>
            <RouteLink
              className={isCurrent("/assessments") ? "nav-link nav-link--active" : "nav-link"}
              to="/assessments/new"
              navigate={navigate}
              aria-current={isCurrent("/assessments") ? "page" : undefined}
            >
              New assessment
            </RouteLink>
            <RouteLink
              className={isCurrent("/administration") ? "nav-link nav-link--active" : "nav-link"}
              to="/administration"
              navigate={navigate}
              aria-current={isCurrent("/administration") ? "page" : undefined}
            >
              Administration
            </RouteLink>
          </nav>
        </div>
      </header>
      <main id="main-content" className="workspace-content" ref={mainRef} tabIndex={-1}>
        {children}
      </main>
      <footer className="footer">
        NimbusX presents source-backed assessment evidence. It does not fabricate missing observations,
        forecasts, or risk decisions.
      </footer>
    </div>
  );
}

export function PageHeader(props: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        {props.eyebrow ? <p className="eyebrow">{props.eyebrow}</p> : null}
        <h1>{props.title}</h1>
        <p className="page-header__description">{props.description}</p>
      </div>
      {props.actions ? <div className="page-header__actions">{props.actions}</div> : null}
    </header>
  );
}

export function StatusPill(props: { status: AnalysisStatus }) {
  const value = props.status;
  const statusClass =
    value === "complete"
      ? "status-pill--complete"
      : value === "partial"
        ? "status-pill--partial"
        : value === "failed" || value === "expired"
          ? "status-pill--failed"
          : "status-pill--pending";

  return <span className={"status-pill " + statusClass}>{titleCase(value)}</span>;
}

export function DecisionPill(props: {
  decision: AnalysisDecision | Decision | null | undefined;
}) {
  if (!props.decision) {
    return <span className="muted">No decision issued</span>;
  }

  const decision = typeof props.decision === "string" ? props.decision : props.decision.status;
  const severity =
    decision === "acceptable"
      ? "decision-pill--acceptable"
      : decision === "mitigation_required"
        ? "decision-pill--mitigation"
        : decision === "high_risk"
          ? "decision-pill--high"
          : "decision-pill--insufficient";

  return <span className={"decision-pill " + severity}>{titleCase(decision)}</span>;
}

export function Notice(props: {
  tone: "info" | "warning" | "error" | "success";
  title?: string;
  children: ReactNode;
}) {
  return (
    <section className={"notice notice--" + props.tone} role={props.tone === "error" ? "alert" : "status"}>
      {props.title ? <strong>{props.title}</strong> : null}
      <div>{props.children}</div>
    </section>
  );
}

export function LoadingPanel(props: { label?: string }) {
  return (
    <section className="loading-panel" aria-live="polite" aria-busy="true">
      <span className="spinner" aria-hidden="true" />
      <span>{props.label ?? "Loading source-backed workspace data..."}</span>
    </section>
  );
}

export function EmptyState(props: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="empty-state">
      <h2>{props.title}</h2>
      <p>{props.children}</p>
      {props.action ? <div className="empty-state__action">{props.action}</div> : null}
    </section>
  );
}

function requestIdFromError(error: unknown): string | null {
  if (
    typeof error === "object" &&
    error !== null &&
    "requestId" in error &&
    typeof error.requestId === "string"
  ) {
    return error.requestId;
  }
  return null;
}

export function ErrorPanel(props: { error: unknown; title?: string; onRetry?: () => void }) {
  const message = props.error instanceof Error ? props.error.message : "An unexpected error occurred.";
  const requestId = requestIdFromError(props.error);
  return (
    <Notice tone="error" title={props.title ?? "Request unavailable"}>
      <p>{message}</p>
      {requestId ? <p className="table-detail">Request ID: {requestId}</p> : null}
      {props.onRetry ? (
        <button className="button button--secondary" type="button" onClick={props.onRetry}>
          Try again
        </button>
      ) : null}
    </Notice>
  );
}

export function DefinitionList(props: {
  items: Array<{ term: string; description: ReactNode }>;
}) {
  return (
    <dl className="definition-list">
      {props.items.map((item) => (
        <div key={item.term}>
          <dt>{item.term}</dt>
          <dd>{item.description}</dd>
        </div>
      ))}
    </dl>
  );
}