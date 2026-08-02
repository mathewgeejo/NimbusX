import { RouteLink } from "./ui";

type ProjectSection = "sites" | "assets" | "alerts";
type AnalysisSection = "summary" | "evidence" | "compare" | "report";

function projectPath(projectId: string, suffix = ""): string {
  return "/projects/" + encodeURIComponent(projectId) + suffix;
}

export function ProjectWorkspaceNav(props: {
  projectId: string;
  active: ProjectSection;
  navigate: (to: string) => void;
}) {
  const { projectId, active, navigate } = props;
  const items: Array<{ key: ProjectSection; label: string; to: string }> = [
    { key: "sites", label: "Sites & assessments", to: projectPath(projectId) },
    { key: "assets", label: "Asset inventory", to: projectPath(projectId, "/assets") },
    { key: "alerts", label: "Alert rules & events", to: projectPath(projectId, "/alerts") }
  ];

  return (
    <nav className="workspace-nav" aria-label="Project workspace">
      {items.map((item) => (
        <RouteLink
          key={item.key}
          className={item.key === active ? "workspace-nav__link workspace-nav__link--active" : "workspace-nav__link"}
          to={item.to}
          navigate={navigate}
          aria-current={item.key === active ? "page" : undefined}
        >
          {item.label}
        </RouteLink>
      ))}
    </nav>
  );
}

export function AnalysisWorkspaceNav(props: {
  analysisId: string;
  active: AnalysisSection;
  navigate: (to: string) => void;
}) {
  const { analysisId, active, navigate } = props;
  const basePath = "/analyses/" + encodeURIComponent(analysisId);
  const items: Array<{ key: AnalysisSection; label: string; to: string }> = [
    { key: "summary", label: "Assessment", to: basePath },
    { key: "evidence", label: "Evidence", to: basePath + "/evidence" },
    { key: "compare", label: "Review", to: basePath + "/compare" },
    { key: "report", label: "Report", to: basePath + "/report" }
  ];

  return (
    <nav className="workspace-nav workspace-nav--analysis" aria-label="Assessment workspace">
      {items.map((item) => (
        <RouteLink
          key={item.key}
          className={item.key === active ? "workspace-nav__link workspace-nav__link--active" : "workspace-nav__link"}
          to={item.to}
          navigate={navigate}
          aria-current={item.key === active ? "page" : undefined}
        >
          {item.label}
        </RouteLink>
      ))}
    </nav>
  );
}
