import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Project } from "../api/contracts";
import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  Notice,
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
        title="Start your climate-risk workspace"
        description="Create a project, add a location, then run a source-backed assessment. The steps below keep the first setup simple."
      />

      <Notice tone="info" title="Start here">
        <ol className="getting-started-list">
          <li>Create a project using the form below.</li>
          <li>Open the project and add a point site with its local time zone.</li>
          <li>Run an assessment, then review its evidence and limitations before acting on it.</li>
        </ol>
      </Notice>

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
              Create your first project to keep its locations, assessments, and evidence together.
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
          <h2 id="create-project-title">Create your first project</h2>
          <p className="subtle">
            Give it a clear name, such as a portfolio, facility group, or client workstream. This local
            development build stores workspace data only while the API is running.
          </p>
          <form className="stack-form" onSubmit={(event) => void createProject(event)} noValidate>
            <label htmlFor="project-name">
              Project name
              <input
                id="project-name"
                name="project-name"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                placeholder="e.g. Northern facilities"
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
