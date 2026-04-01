// this file renders one top level metric card
import clsx from "clsx";

type StatCardProps = {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "good" | "warn";
};

export function StatCard({ label, value, hint, tone = "default" }: StatCardProps) {
  // this component standardizes metric cards used in overview
  return (
    <div className={clsx("stat-card", tone)}>
      <p className="stat-label">{label}</p>
      <h3 className="stat-value">{value}</h3>
      {hint ? <p className="stat-hint">{hint}</p> : null}
    </div>
  );
}
