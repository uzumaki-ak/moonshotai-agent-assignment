// this file renders empty state for no data screens

type EmptyStateProps = {
  title: string;
  subtitle: string;
};

export function EmptyState({ title, subtitle }: EmptyStateProps) {
  // this component keeps no data views clean and consistent
  return (
    <div className="empty-state">
      <h4>{title}</h4>
      <p>{subtitle}</p>
    </div>
  );
}
