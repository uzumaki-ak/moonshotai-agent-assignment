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
          <XAxis dataKey="date" tick={{ fill: "#b9b8b4", fontSize: 11 }} />
          <YAxis domain={[-1, 1]} tick={{ fill: "#b9b8b4", fontSize: 11 }} />
          <Tooltip />
          <Line type="monotone" dataKey="sentiment" stroke="#f5f5f5" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
