import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useLaunchParams } from "@telegram-apps/sdk-react";

/**
 * Route an invite that arrived as a launch parameter.
 *
 * A `t.me/<bot>?startapp=<code>` link opens the Mini App at its configured base URL
 * and delivers the code out-of-band as `start_param` — the path is always "/". Nothing
 * read that parameter before, so everyone following an invite landed on the home screen
 * and had to find the session themselves.
 *
 * Deep links that carry a real path (`/session/<code>` from a bot web_app button) need
 * no help; this only fires at the root so it can never fight an explicit route.
 */
export function useStartParam() {
  const navigate = useNavigate();
  const location = useLocation();
  const lp = useLaunchParams();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current || location.pathname !== "/") return;

    // sdk-react v2 exposes start_param as `startParam` (same generation as the
    // `initDataRaw` used in useTelegram.ts). Fall back to the query string for the
    // case where the app is opened by URL rather than by t.me link.
    const fromLaunch = lp.startParam;
    const fromQuery = new URLSearchParams(window.location.search).get("startapp");
    const code = fromLaunch || fromQuery;
    if (!code) return;

    handled.current = true;
    navigate(`/session/${code}`, { replace: true });
  }, [lp, location.pathname, navigate]);
}
