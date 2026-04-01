// this file renders side by side brand comparison page
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchBrandComparison, fetchBrands } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";
import { SentimentPill } from "../components/SentimentPill";
import { ComparisonBarChart } from "../components/charts/ComparisonBarChart";

function formatInr(value: number | null) {
  // this helper formats inr values
  if (value === null) return "na";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

export function ComparePage() {
  // this page compares brands with filter and chart
  const [selectedBrandIds, setSelectedBrandIds] = useState<number[]>([]);

  const brandsQuery = useQuery({ queryKey: ["brands"], queryFn: fetchBrands });
  const compareQuery = useQuery({
    queryKey: ["brand-compare", selectedBrandIds],
    queryFn: () => fetchBrandComparison(selectedBrandIds),
  });

  const rows = compareQuery.data ?? [];

  const toggleBrand = (brandId: number) => {
    // this handler toggles one brand in active filter list
    setSelectedBrandIds((prev) => (prev.includes(brandId) ? prev.filter((id) => id !== brandId) : [...prev, brandId]));
  };

  const topPerformer = useMemo(() => {
    if (!rows.length) return null;
    return [...rows]
      .filter((row) => row.sentiment_score !== null)
      .sort((a, b) => (b.sentiment_score ?? -999) - (a.sentiment_score ?? -999))[0];
  }, [rows]);

  return (
    <section className="page-grid">
      <div className="card">
        <div className="card-head">
          <h3>brand filter</h3>
        </div>
        <div className="chip-list">
          {(brandsQuery.data ?? []).map((brand) => (
            <button
              type="button"
              key={brand.id}
              className={selectedBrandIds.includes(brand.id) ? "chip active" : "chip"}
              onClick={() => toggleBrand(brand.id)}
            >
              {brand.name}
            </button>
          ))}
        </div>
      </div>

      {topPerformer ? (
        <div className="card banner">
          <h3>{topPerformer.brand_name} currently leads sentiment</h3>
          <p>
            this brand shows {topPerformer.sentiment_score?.toFixed(3)} sentiment with avg price {formatInr(topPerformer.avg_price)}.
          </p>
        </div>
      ) : null}

      <ComparisonBarChart data={rows} />

      <div className="card">
        <div className="card-head">
          <h3>comparison table</h3>
        </div>

        {!rows.length ? (
          <EmptyState title="no rows" subtitle="collect and analyze data to unlock comparison" />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>brand</th>
                  <th>price</th>
                  <th>discount</th>
                  <th>rating</th>
                  <th>reviews</th>
                  <th>sentiment</th>
                  <th>premium index</th>
                  <th>value score</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.brand_id}>
                    <td>{row.brand_name}</td>
                    <td>{formatInr(row.avg_price)}</td>
                    <td>{row.avg_discount_pct?.toFixed(2) ?? "na"}%</td>
                    <td>{row.avg_rating?.toFixed(2) ?? "na"}</td>
                    <td>{row.review_count}</td>
                    <td>
                      <SentimentPill score={row.sentiment_score} />
                    </td>
                    <td>{row.premium_index?.toFixed(3) ?? "na"}</td>
                    <td>{row.value_for_money?.toFixed(3) ?? "na"}</td>
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
