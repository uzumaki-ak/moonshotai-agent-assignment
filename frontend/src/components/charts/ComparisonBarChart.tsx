// this file renders compare chart for price and sentiment
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { BrandComparisonRow } from "../../types/api";

type ComparisonBarChartProps = {
  data: BrandComparisonRow[];
};

export function ComparisonBarChart({ data }: ComparisonBarChartProps) {
  // this component gives a quick side by side benchmark view
  const chartData = data.map((row) => ({
    brand: row.brand_name,
    avg_price: row.avg_price ?? 0,
    sentiment_scaled: (row.sentiment_score ?? 0) * 1000,
  }));

  return (
    <div className="card chart-card">
      <div className="card-head">
        <h3>price vs sentiment signal</h3>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
          <XAxis dataKey="brand" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="avg_price" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
          <Bar dataKey="sentiment_scaled" fill="#22d3ee" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
