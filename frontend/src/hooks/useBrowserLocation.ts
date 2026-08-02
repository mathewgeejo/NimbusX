import { useCallback, useEffect, useState } from "react";

function currentPath(): string {
  return window.location.pathname || "/";
}

export interface BrowserLocation {
  pathname: string;
  navigate: (to: string) => void;
}

export function useBrowserLocation(): BrowserLocation {
  const [pathname, setPathname] = useState(currentPath);

  useEffect(() => {
    const onPopState = () => setPathname(currentPath());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = useCallback((to: string) => {
    if (to === currentPath()) {
      return;
    }

    window.history.pushState({}, "", to);
    setPathname(to);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return { pathname, navigate };
}
