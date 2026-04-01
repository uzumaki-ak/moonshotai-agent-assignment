// this file renders dashboard home overview page
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchBrandComparison, fetchOverview } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";
import { SentimentPill } from "../components/SentimentPill";
import { StatCard } from "../components/StatCard";
import { PriceBandChart } from "../components/charts/PriceBandChart";
import { TrendChart } from "../components/charts/TrendChart";

function formatInr(value: number | null) {
  // this helper formats inr values for cards and tables
  if (value === null) return "na";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

export function OverviewPage() {
  // this page summarizes top level metrics and brand winners
  const overviewQuery = useQuery({ queryKey: ["overview"], queryFn: fetchOverview });
  const compareQuery = useQuery({ queryKey: ["brand-compare"], queryFn: () => fetchBrandComparison([]) });

  if (overviewQuery.isLoading) {
    return <div className="loader">loading overview</div>;
  }

  if (!overviewQuery.data) {
    return <EmptyState title="no overview yet" subtitle="run scraper then analysis from pipeline tab" />;
  }

  const stats = overviewQuery.data.stats;
  const compareRows = compareQuery.data ?? [];

  return (
    <section className="page-grid">
      <div className="stat-grid">
        <StatCard label="brands tracked" value={String(stats.total_brands)} hint="minimum 4 needed" />
        <StatCard label="products analyzed" value={String(stats.total_products)} />
        <StatCard label="reviews analyzed" value={String(stats.total_reviews)} />
        <StatCard label="avg sentiment" value={stats.avg_sentiment?.toFixed(3) ?? "na"} tone={(stats.avg_sentiment ?? 0) > 0 ? "good" : "warn"} />
        <StatCard label="avg price" value={formatInr(stats.avg_price)} />
      </div>

      <div className="two-col">
        <TrendChart data={overviewQuery.data.sentiment_trend} />
        <PriceBandChart data={overviewQuery.data.price_bands} />
      </div>

      <div className="card">
        <div className="card-head">
          <h3>quick brand view</h3>
          <Link to="/compare" className="ghost-link">
            open compare
          </Link>
        </div>

        {compareRows.length === 0 ? (
          <EmptyState title="no comparison rows" subtitle="run analysis job to compute metrics" />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>brand</th>
                  <th>avg price</th>
                  <th>discount</th>
                  <th>rating</th>
                  <th>sentiment</th>
                  <th>details</th>
                </tr>
              </thead>
              <tbody>
                {compareRows.slice(0, 6).map((row) => (
                  <tr key={row.brand_id}>
                    <td>{row.brand_name}</td>
                    <td>{formatInr(row.avg_price)}</td>
                    <td>{row.avg_discount_pct ? `${row.avg_discount_pct.toFixed(1)}%` : "na"}</td>
                    <td>{row.avg_rating?.toFixed(2) ?? "na"}</td>
                    <td>
                      <SentimentPill score={row.sentiment_score} />
                    </td>
                    <td>
                      <Link to={`/brands/${row.brand_id}`} className="ghost-link">
                        view
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
