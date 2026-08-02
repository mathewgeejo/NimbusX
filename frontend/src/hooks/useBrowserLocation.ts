import { useCallback, useEffect, useState } from "react";

function currentPath(): string {
  return window.location.pathname || "/";
}

function currentSearch(): string {
  return window.location.search;
}

export interface BrowserLocation {
  pathname: string;
  search: string;
  navigate: (to: string) => void;
}

export function useBrowserLocation(): BrowserLocation {
  const [pathname, setPathname] = useState(currentPath);
  const [search, setSearch] = useState(currentSearch);

  useEffect(() => {
    const onPopState = () => {
      setPathname(currentPath());
      setSearch(currentSearch());
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = useCallback((to: string) => {
    if (to === currentPath() + currentSearch()) {
      return;
    }

    window.history.pushState({}, "", to);
    setPathname(currentPath());
    setSearch(currentSearch());
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return { pathname, search, navigate };
}
