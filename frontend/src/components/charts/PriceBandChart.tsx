// this file renders price band distribution chart
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const colors = ["#fafafa", "#d4d4d8", "#71717a"];

type PriceBandChartProps = {
  data: Array<{ band: string; product_count: number }>;
};

export function PriceBandChart({ data }: PriceBandChartProps) {
  // this component visualizes value mid premium product split
  return (
    <div className="card chart-card">
      <div className="card-head">
        <h3>price band mix</h3>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie data={data} dataKey="product_count" nameKey="band" cx="50%" cy="50%" outerRadius={88} label>
            {data.map((entry, index) => (
              <Cell key={`${entry.band}-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
