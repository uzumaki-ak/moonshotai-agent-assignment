// this file renders side by side brand comparison page
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchBrandComparison, fetchBrands } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";
import { SentimentPill } from "../components/SentimentPill";
import { ComparisonBarChart } from "../components/charts/ComparisonBarChart";
import type { BrandComparisonRow } from "../types/api";

function formatInr(value: number | null) {
  // this helper formats inr values
  if (value === null) return "na";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

type SortKey = "brand_name" | "avg_price" | "avg_discount_pct" | "avg_rating" | "review_count" | "premium_index" | "value_for_money";

export function ComparePage() {
  // this page compares brands with scalable filter and sortable table
  const [selectedBrandIds, setSelectedBrandIds] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("avg_price");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

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

  const filteredBrands = useMemo(() => {
    const all = brandsQuery.data ?? [];
    const query = search.trim().toLowerCase();
    if (!query) return all;
    return all.filter((brand) => brand.name.toLowerCase().includes(query));
  }, [brandsQuery.data, search]);

  const sortedRows = useMemo(() => {
    const clone = [...rows];
    clone.sort((a, b) => {
      const left = a[sortKey];
      const right = b[sortKey];

      if (sortKey === "brand_name") {
        const lv = String(left ?? "");
        const rv = String(right ?? "");
        return sortDir === "asc" ? lv.localeCompare(rv) : rv.localeCompare(lv);
      }

      const lv = typeof left === "number" ? left : -999999;
      const rv = typeof right === "number" ? right : -999999;
      return sortDir === "asc" ? lv - rv : rv - lv;
    });
    return clone;
  }, [rows, sortDir, sortKey]);

  const chartRows = useMemo(() => {
    // this section keeps chart readable for large brand sets
    return sortedRows.slice(0, 12);
  }, [sortedRows]);

  const topPerformer = useMemo(() => {
    if (!rows.length) return null;
    return [...rows]
      .filter((row) => row.sentiment_score !== null)
      .sort((a, b) => (b.sentiment_score ?? -999) - (a.sentiment_score ?? -999))[0];
  }, [rows]);

  const updateSort = (key: SortKey) => {
    // this handler toggles sorting for comparison table
    if (sortKey === key) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDir("desc");
  };

  return (
    <section className="page-grid">
      <div className="card">
        <div className="card-head">
          <h3>brand filter</h3>
          <small>{selectedBrandIds.length ? `${selectedBrandIds.length} selected` : "all brands"}</small>
        </div>

        <div className="form-inline">
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="search brands" />
        </div>

        <div className="chip-list scroll-chip-list">
          {filteredBrands.map((brand) => (
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
      ) : (
        <div className="card banner">
          <h3>sentiment is unavailable</h3>
          <p>reviews were not captured in this run. open pipeline and inspect scrape artifacts or retry scrape.</p>
        </div>
      )}

      <ComparisonBarChart data={chartRows} />

      <div className="card">
        <div className="card-head">
          <h3>comparison table</h3>
          <small>sorted by {sortKey.replace(/_/g, " ")} ({sortDir})</small>
        </div>

        {!sortedRows.length ? (
          <EmptyState title="no rows" subtitle="collect and analyze data to unlock comparison" />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>
                    <button type="button" className="table-sort" onClick={() => updateSort("brand_name")}>brand</button>
                  </th>
                  <th>
                    <button type="button" className="table-sort" onClick={() => updateSort("avg_price")}>price</button>
                  </th>
                  <th>
                    <button type="button" className="table-sort" onClick={() => updateSort("avg_discount_pct")}>discount</button>
                  </th>
                  <th>
                    <button type="button" className="table-sort" onClick={() => updateSort("avg_rating")}>rating</button>
                  </th>
                  <th>
                    <button type="button" className="table-sort" onClick={() => updateSort("review_count")}>reviews</button>
                  </th>
                  <th>sentiment</th>
                  <th>
                    <button type="button" className="table-sort" onClick={() => updateSort("premium_index")}>premium index</button>
                  </th>
                  <th>
                    <button type="button" className="table-sort" onClick={() => updateSort("value_for_money")}>value score</button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row: BrandComparisonRow) => (
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
