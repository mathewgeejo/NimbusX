import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RouteLink, WorkspaceShell } from "./ui";

describe("workspace navigation accessibility", () => {
  afterEach(() => {
    cleanup();
  });

  it("moves focus to the main landmark after a client-side route change", async () => {
    const navigate = vi.fn();
    const { rerender } = render(
      <WorkspaceShell pathname="/portfolio" navigate={navigate}>
        <h1>Portfolio</h1>
      </WorkspaceShell>
    );
    const main = screen.getByRole("main");

    rerender(
      <WorkspaceShell pathname="/administration" navigate={navigate}>
        <h1>Administration</h1>
      </WorkspaceShell>
    );

    await waitFor(() => expect(document.activeElement).toBe(main));
  });

  it("uses client navigation for ordinary clicks but preserves modified-link behavior", () => {
    const navigate = vi.fn();
    const { getByRole } = render(
      <RouteLink to="#portfolio" navigate={navigate}>
        Portfolio
      </RouteLink>
    );
    const link = getByRole("link", { name: "Portfolio" });

    fireEvent.click(link);
    expect(navigate).toHaveBeenCalledWith("#portfolio");

    navigate.mockClear();
    fireEvent.click(link, { shiftKey: true });
    expect(navigate).not.toHaveBeenCalled();
  });
});