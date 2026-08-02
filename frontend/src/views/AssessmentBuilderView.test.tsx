import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AssessmentBuilderView } from "./AssessmentBuilderView";

describe("AssessmentBuilderView", () => {
  it("uses a saved project and site supplied by the guided site flow", () => {
    render(
      <AssessmentBuilderView
            navigate={vi.fn()}
            initialProjectId="project-123"
            initialSiteId="site-456"
            initialTimezone="America/New_York"
      />
    );

    expect(screen.getByLabelText(/Project ID/)).toHaveValue("project-123");
    expect(screen.getByLabelText(/Existing site ID/)).toHaveValue("site-456");
    expect(screen.getByLabelText("Local time zone")).toHaveValue("America/New_York");
    expect(screen.getByText("Saved site selected")).toBeInTheDocument();
  });
});
