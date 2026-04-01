// this file wraps page content with shared layout
import type { PropsWithChildren } from "react";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function PageShell({ children }: PropsWithChildren) {
  // this component provides stable frame for every route
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="content-shell">
        <Topbar />
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
