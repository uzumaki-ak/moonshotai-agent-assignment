// this file renders generated agent insights page
import { useQuery } from "@tanstack/react-query";

import { fetchInsights } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";

export function InsightsPage() {
  // this page shows non obvious conclusions generated from metrics
  const insightsQuery = useQuery({ queryKey: ["insights"], queryFn: fetchInsights });
  const insights = insightsQuery.data ?? [];

  return (
    <section className="page-grid">
      <div className="card banner">
        <h3>agent insights</h3>
        <p>these cards combine quantitative metrics with theme signals to explain who is winning and why.</p>
      </div>

      {!insights.length ? (
        <EmptyState title="no insights yet" subtitle="run analysis job to generate insights" />
      ) : (
        <div className="insight-grid">
          {insights.map((insight) => (
            <article className="card insight-card" key={insight.id}>
              <div className="card-head">
                <h3>{insight.title}</h3>
                <span className="pill neutral">{insight.insight_type}</span>
              </div>
              <p>{insight.body}</p>
              <small>confidence {insight.confidence?.toFixed(2) ?? "na"}</small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
