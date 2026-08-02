import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Project } from "../api/contracts";
import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  PageHeader,
  RouteLink
} from "../components/ui";
import { displayDateTime } from "../lib/time";

export function PortfolioView(props: { navigate: (to: string) => void }) {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [projectName, setProjectName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<unknown>(null);

  const loadProjects = useCallback(async () => {
    setError(null);
    try {
      setProjects(await api.listProjects());
    } catch (requestError) {
      setError(requestError);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = projectName.trim();
    if (!name) {
      setCreateError(new Error("Enter a project name before creating it."));
      return;
    }

    setCreating(true);
    setCreateError(null);
    try {
      const project = await api.createProject({ name });
      setProjectName("");
      setProjects((current) => [project, ...(current ?? [])]);
      props.navigate("/projects/" + project.id);
    } catch (requestError) {
      setCreateError(requestError);
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Portfolio"
        title="Climate risk, with the evidence attached"
        description="Organize point sites and project-linked assessments while this development process is running. NimbusX does not prepopulate a portfolio with sample risks."
        actions={
          <div className="button-group">
            <RouteLink className="button button--secondary" to="/operations" navigate={props.navigate}>
              Operations
            </RouteLink>
            <RouteLink className="button button--primary" to="/assessments/new" navigate={props.navigate}>
              Start an assessment
            </RouteLink>
          </div>
        }
      />

      <section className="surface portfolio-intro" aria-labelledby="portfolio-workflow">
        <div>
          <p className="eyebrow">Evidence-first workflow</p>
          <h2 id="portfolio-workflow">Create a project, add a site, then assess a defined time window.</h2>
        </div>
        <p>
          Assessments run asynchronously and show source provenance, limitations, and a report version.
          This development foundation stores workspace records only in process memory, so data is lost when
          the API restarts. A decision is withheld when required evidence is incomplete.
        </p>
      </section>

      <section className="portfolio-workspace-links" aria-label="Portfolio workspace tools">
        <RouteLink className="workspace-link-card" to="/operations" navigate={props.navigate}>
          <span className="eyebrow">Operational controls</span>
          <strong>Define threshold and review patterns</strong>
          <span>Use named, evidence-linked alert rules rather than informal weather checks.</span>
        </RouteLink>
        <RouteLink className="workspace-link-card" to="/assessments/new" navigate={props.navigate}>
          <span className="eyebrow">Assessment builder</span>
          <strong>Run an explicit local time-window analysis</strong>
          <span>Choose a site, horizon, and thresholds without silently filling missing data.</span>
        </RouteLink>
      </section>

      <div className="two-column">
        <section className="surface" aria-labelledby="project-list-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Projects</p>
              <h2 id="project-list-title">Your portfolio</h2>
            </div>
            <button className="button button--secondary" type="button" onClick={() => void loadProjects()}>
              Refresh
            </button>
          </div>

          {projects === null && !error ? <LoadingPanel label="Loading projects…" /> : null}
          {error ? <ErrorPanel error={error} onRetry={() => void loadProjects()} /> : null}
          {projects && projects.length === 0 ? (
            <EmptyState title="No projects yet" action={null}>
              Create a project to group stored sites and project-linked assessments in this development process.
            </EmptyState>
          ) : null}
          {projects && projects.length > 0 ? (
            <ul className="project-list">
              {projects.map((project) => (
                <li key={project.id}>
                  <RouteLink to={"/projects/" + project.id} navigate={props.navigate} className="project-card">
                    <span>
                      <strong>{project.name}</strong>
                      <small>Created {displayDateTime(project.created_at)}</small>
                    </span>
                    <span aria-hidden="true">Open</span>
                  </RouteLink>
                </li>
              ))}
            </ul>
          ) : null}
        </section>

        <section className="surface" aria-labelledby="create-project-title">
          <p className="eyebrow">New project</p>
          <h2 id="create-project-title">Set up a portfolio container</h2>
          <p className="subtle">
            Project names are organizational labels only; they do not imply that an assessment has been
            run or approved.
          </p>
          <form className="stack-form" onSubmit={(event) => void createProject(event)} noValidate>
            <label htmlFor="project-name">
              Project name
              <input
                id="project-name"
                name="project-name"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                autoComplete="off"
                maxLength={160}
                required
              />
            </label>
            {createError ? <ErrorPanel error={createError} /> : null}
            <button className="button button--primary" type="submit" disabled={creating}>
              {creating ? "Creating project…" : "Create project"}
            </button>
          </form>
        </section>
      </div>
    </>
  );
}
