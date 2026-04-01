// this file renders sentiment trend over recent dates
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type TrendChartProps = {
  data: Array<{ date: string; sentiment: number }>;
};

export function TrendChart({ data }: TrendChartProps) {
  // this component helps detect sentiment drift over time
  return (
    <div className="card chart-card">
      <div className="card-head">
        <h3>sentiment trend</h3>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 12, right: 10, bottom: 4, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.14)" />
          <XAxis dataKey="date" tick={{ fill: "#d7dce4", fontSize: 11 }} />
          <YAxis domain={[-1, 1]} tick={{ fill: "#d7dce4", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "transparent", border: "none", boxShadow: "none", padding: 0 }}
            labelStyle={{ display: "none" }}
            formatter={(value: number) => [`sentiment ${value.toFixed(4)}`, "score"]}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="chart-tooltip">
                  <div className="label">{label}</div>
                  <div className="value">sentiment {(payload[0].value as number).toFixed(4)}</div>
                </div>
              );
            }}
          />
          <Line type="monotone" dataKey="sentiment" stroke="var(--chart-1)" strokeWidth={2.5} dot={{ fill: "#f8fafc", r: 4 }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
