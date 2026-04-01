// this file renders price band distribution chart
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const colors = ["var(--chart-1)", "var(--chart-3)", "var(--chart-2)"];

type PriceBandChartProps = {
  data: Array<{ band: string; product_count: number }>;
};

export function PriceBandChart({ data }: PriceBandChartProps) {
  // this component visualizes value mid premium product split
  const renderLabel = (props: { cx?: number; cy?: number; midAngle?: number; outerRadius?: number; name?: string; value?: number }) => {
    const { cx = 0, cy = 0, midAngle = 0, outerRadius = 0, name = "", value = 0 } = props;
    const radius = outerRadius + 22;
    const x = cx + radius * Math.cos((-midAngle * Math.PI) / 180);
    const y = cy + radius * Math.sin((-midAngle * Math.PI) / 180);

    return (
      <text x={x} y={y} fill="#f8fafc" textAnchor={x > cx ? "start" : "end"} dominantBaseline="central" fontSize={12}>
        {`${name}: ${value}`}
      </text>
    );
  };

  return (
    <div className="card chart-card">
      <div className="card-head">
        <h3>price band mix</h3>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            dataKey="product_count"
            nameKey="band"
            cx="50%"
            cy="50%"
            outerRadius={88}
            label={renderLabel}
            labelLine={{ stroke: "rgba(255,255,255,0.35)" }}
          >
            {data.map((entry, index) => (
              <Cell key={`${entry.band}-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: "transparent", border: "none", boxShadow: "none", padding: 0 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const item = payload[0];
              return (
                <div className="chart-tooltip">
                  <div className="label">{String(item.name)}</div>
                  <div className="value">products {String(item.value)}</div>
                </div>
              );
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
