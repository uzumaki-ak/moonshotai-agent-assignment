// this file renders left navigation for all dashboard pages
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "overview" },
  { to: "/compare", label: "brand compare" },
  { to: "/insights", label: "agent insights" },
  { to: "/chat", label: "ask data" },
  { to: "/pipeline", label: "pipeline" },
];

export function Sidebar() {
  // this component shows route navigation and app identity
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <span className="brand-dot" />
        <div>
          <h1>moonshot ai</h1>
          <p>luggage intelligence</p>
        </div>
      </div>

      <nav className="nav-list">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <p>market</p>
        <p>amazon india</p>
      </div>
    </aside>
  );
}
