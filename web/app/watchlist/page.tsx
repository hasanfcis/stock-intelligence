import { getLatestReport, getUniverse } from "@/lib/api";
import { StockTable } from "@/components/StockTable";
import { EmptyState } from "@/components/EmptyState";

export const dynamic = "force-dynamic";

export default async function WatchlistPage() {
  const [report, universe] = await Promise.all([getLatestReport(), getUniverse()]);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-lg">Watchlist</h1>

      {!report ? (
        <EmptyState
          title="No report yet"
          detail="Run the pipeline to populate scores for your configured universe."
        />
      ) : (
        <div className="panel overflow-hidden">
          <StockTable scores={report.scores} />
        </div>
      )}

      {universe && universe.excluded.length > 0 && (
        <section>
          <h2 className="text-sm text-muted mb-3">Excluded from universe</h2>
          <ul className="panel px-4 py-3 flex flex-col gap-2">
            {universe.excluded.map((e) => (
              <li key={e.symbol} className="text-sm flex gap-2">
                <span className="font-mono text-muted">{e.symbol}</span>
                <span className="text-muted">— {e.reason} ({e.rule_id})</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
