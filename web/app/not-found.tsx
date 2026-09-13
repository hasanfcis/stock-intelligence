import Link from "next/link";

export default function NotFound() {
  return (
    <div className="panel px-6 py-10 text-center">
      <div className="text-sm text-ink mb-1">Not found</div>
      <div className="text-sm text-muted mb-4">
        That ticker isn&apos;t in the latest report, or no report has run yet.
      </div>
      <Link href="/" className="text-sm text-amber hover:underline">
        Back to dashboard
      </Link>
    </div>
  );
}
