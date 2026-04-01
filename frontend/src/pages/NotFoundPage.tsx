// this file renders fallback page for unknown routes
import { Link } from "react-router-dom";

export function NotFoundPage() {
  // this page handles invalid paths
  return (
    <section className="page-grid">
      <div className="card banner">
        <h3>route not found</h3>
        <p>go back to dashboard overview.</p>
        <Link className="ghost-link" to="/">
          back home
        </Link>
      </div>
    </section>
  );
}
