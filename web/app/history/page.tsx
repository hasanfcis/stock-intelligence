import { getHistory } from "@/lib/api";
import { EmptyState } from "@/components/EmptyState";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const history = await getHistory();
  const hasBuckets = history.buckets.some((b) => b.count > 0);

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-lg">History</h1>

      {!hasBuckets ? (
        <EmptyState
          title="Not enough measured history yet"
          detail={
            history.note ??
            "Once the scheduler has run for a few weeks, this screen shows forward returns and win rate by score bucket."
          }
        />
      ) : (
        <>
          <section>
            <h2 className="text-sm text-muted mb-3">Performance by score bucket</h2>
            <table className="w-full hairline-table panel">
              <thead>
                <tr>
                  <th>Score bucket</th>
                  <th>Count</th>
                  <th>Avg 5-day return</th>
                  <th>Avg 20-day return</th>
                  <th>Win rate</th>
                </tr>
              </thead>
              <tbody>
                {history.buckets.map((b) => (
                  <tr key={b.bucket}>
                    <td className="font-mono">{b.bucket}</td>
                    <td className="font-mono tabular-nums text-muted">{b.count}</td>
                    <td className="font-mono tabular-nums">
                      {b.avg_5d_return !== null ? `${b.avg_5d_return >= 0 ? "+" : ""}${b.avg_5d_return}%` : "\u2014"}
                    </td>
                    <td className="font-mono tabular-nums">
                      {b.avg_20d_return !== null ? `${b.avg_20d_return >= 0 ? "+" : ""}${b.avg_20d_return}%` : "\u2014"}
                    </td>
                    <td className="font-mono tabular-nums">
                      {b.win_rate !== null ? `${b.win_rate}%` : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2 className="text-sm text-muted mb-3">Recommendation log</h2>
            <table className="w-full hairline-table panel">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Ticker</th>
                  <th>Setup</th>
                  <th>Score</th>
                  <th>5-day</th>
                  <th>20-day</th>
                </tr>
              </thead>
              <tbody>
                {history.items.map((item, i) => (
                  <tr key={i}>
                    <td className="font-mono text-muted">{item.as_of}</td>
                    <td className="font-mono">{item.ticker}</td>
                    <td>{item.action_category}</td>
                    <td className="font-mono tabular-nums">{item.overall_score.toFixed(0)}</td>
                    <td className="font-mono tabular-nums">
                      {item.forward_5d_return !== null
                        ? `${item.forward_5d_return >= 0 ? "+" : ""}${item.forward_5d_return}%`
                        : "pending"}
                    </td>
                    <td className="font-mono tabular-nums">
                      {item.forward_20d_return !== null
                        ? `${item.forward_20d_return >= 0 ? "+" : ""}${item.forward_20d_return}%`
                        : "pending"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  );
}
