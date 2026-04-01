// this file renders top action bar and page title
import { useMemo } from "react";

export function Topbar() {
  // this component shows timestamp of current dashboard session
  const nowLabel = useMemo(() => {
    const formatter = new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
    return formatter.format(new Date());
  }, []);

  return (
    <header className="topbar">
      <div>
        <h2>competitive intelligence dashboard</h2>
        <p>live metrics from amazon india product and review data</p>
      </div>
      <div className="topbar-chip">updated {nowLabel}</div>
    </header>
  );
}
