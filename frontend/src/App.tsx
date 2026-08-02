import type { ReactElement } from "react";
import { WorkspaceShell } from "./components/ui";
import { useBrowserLocation } from "./hooks/useBrowserLocation";
import { AdministrationView } from "./views/AdministrationView";
import { AnalysisView } from "./views/AnalysisView";
import { AssessmentBuilderView } from "./views/AssessmentBuilderView";
import { CompareView } from "./views/CompareView";
import { EvidenceView } from "./views/EvidenceView";
import { PortfolioView } from "./views/PortfolioView";
import { ProjectView } from "./views/ProjectView";
import { ReportView } from "./views/ReportView";

function decodeSegment(value: string | undefined): string | null {
  if (!value) {
    return null;
  }
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

function NotFoundView(props: { navigate: (to: string) => void }) {
  return (
    <section className="surface empty-state">
      <p className="eyebrow">Not found</p>
      <h1>This workspace route does not exist</h1>
      <p>Return to the portfolio to create or open a source-backed assessment.</p>
      <button className="button button--primary" type="button" onClick={() => props.navigate("/portfolio")}>
        Go to portfolio
      </button>
    </section>
  );
}

export default function App() {
  const { pathname, navigate } = useBrowserLocation();
  const segments = pathname.split("/").filter(Boolean);
  let content: ReactElement;

  if (pathname === "/" || pathname === "/portfolio") {
    content = <PortfolioView navigate={navigate} />;
  } else if (pathname === "/assessments/new") {
    content = <AssessmentBuilderView navigate={navigate} />;
  } else if (pathname === "/administration") {
    content = <AdministrationView />;
  } else if (segments[0] === "projects" && segments.length === 2) {
    const projectId = decodeSegment(segments[1]);
    content = projectId ? <ProjectView projectId={projectId} navigate={navigate} /> : <NotFoundView navigate={navigate} />;
  } else if (segments[0] === "analyses" && segments.length >= 2) {
    const analysisId = decodeSegment(segments[1]);
    if (!analysisId) {
      content = <NotFoundView navigate={navigate} />;
    } else if (segments.length === 2) {
      content = <AnalysisView analysisId={analysisId} navigate={navigate} />;
    } else if (segments.length === 3 && segments[2] === "evidence") {
      content = <EvidenceView analysisId={analysisId} navigate={navigate} />;
    } else if (segments.length === 3 && segments[2] === "compare") {
      content = <CompareView analysisId={analysisId} navigate={navigate} />;
    } else if (segments.length === 3 && segments[2] === "report") {
      content = <ReportView analysisId={analysisId} navigate={navigate} />;
    } else {
      content = <NotFoundView navigate={navigate} />;
    }
  } else {
    content = <NotFoundView navigate={navigate} />;
  }

  return (
    <WorkspaceShell pathname={pathname} navigate={navigate}>
      {content}
    </WorkspaceShell>
  );
}