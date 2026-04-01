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
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.14)" />
          <XAxis dataKey="brand" tick={{ fill: "#d7dce4", fontSize: 11 }} />
          <YAxis tick={{ fill: "#d7dce4", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "transparent", border: "none", boxShadow: "none", padding: 0 }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="chart-tooltip">
                  <div className="label">{label}</div>
                  {payload.map((item) => (
                    <div key={item.dataKey as string} className="value">
                      {item.dataKey === "avg_price" ? `avg price ${Number(item.value).toFixed(0)}` : `sentiment signal ${Number(item.value).toFixed(1)}`}
                    </div>
                  ))}
                </div>
              );
            }}
          />
          <Bar dataKey="avg_price" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
          <Bar dataKey="sentiment_scaled" fill="var(--chart-3)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
