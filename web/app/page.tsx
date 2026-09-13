import { getLatestReport } from "@/lib/api";
import { StockTable } from "@/components/StockTable";
import { EmptyState } from "@/components/EmptyState";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const report = await getLatestReport();

  if (!report) {
    return (
      <div>
        <h1 className="text-lg mb-6">Dashboard</h1>
        <EmptyState
          title="No report yet"
          detail={
            'Run the pipeline to see today\u2019s scores: POST /reports/run on the API, or `python -m stock_intel.cli run`.'
          }
        />
      </div>
    );
  }

  const { market_context, scores, negative_catalysts, date } = report;
  const topSetups = scores.slice(0, 5);

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-lg mb-1">Market today</h1>
        <div className="text-sm text-muted">{date}</div>
      </div>

      <div className="grid grid-cols-5 gap-4">
        <MarketStat label="S&P 500" value={`${market_context.spx_change_pct >= 0 ? "+" : ""}${market_context.spx_change_pct}%`} positive={market_context.spx_change_pct >= 0} />
        <MarketStat label="Nasdaq" value={`${market_context.nasdaq_change_pct >= 0 ? "+" : ""}${market_context.nasdaq_change_pct}%`} positive={market_context.nasdaq_change_pct >= 0} />
        <MarketStat label="Semiconductors" value={`${market_context.sox_change_pct >= 0 ? "+" : ""}${market_context.sox_change_pct}%`} positive={market_context.sox_change_pct >= 0} />
        <MarketStat label="10Y yield" value={`${market_context.ten_year_yield}%`} />
        <MarketStat label="VIX" value={`${market_context.vix}`} />
      </div>

      <section>
        <h2 className="text-sm text-muted mb-3">Top opportunities</h2>
        <div className="panel overflow-hidden">
          <StockTable scores={topSetups} />
        </div>
      </section>

      {negative_catalysts.length > 0 && (
        <section>
          <h2 className="text-sm text-muted mb-3">Negative catalysts</h2>
          <div className="panel overflow-hidden">
            <StockTable scores={negative_catalysts} />
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm text-muted mb-3">Full universe</h2>
        <div className="panel overflow-hidden">
          <StockTable scores={scores} />
        </div>
      </section>
    </div>
  );
}

function MarketStat({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  const color =
    positive === undefined ? "text-ink" : positive ? "text-gain" : "text-loss";
  return (
    <div className="panel px-4 py-3">
      <div className="text-xs text-muted mb-1">{label}</div>
      <div className={`font-mono text-lg ${color}`}>{value}</div>
    </div>
  );
}
