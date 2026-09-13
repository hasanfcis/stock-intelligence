export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="panel px-6 py-10 text-center">
      <div className="text-sm text-ink mb-1">{title}</div>
      <div className="text-sm text-muted max-w-md mx-auto">{detail}</div>
    </div>
  );
}
