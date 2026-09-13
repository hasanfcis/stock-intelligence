import Link from "next/link";
import { StockScore } from "@/lib/types";
import { ActionBadge, ScoreValue } from "./ScoreBadge";

export function StockTable({ scores }: { scores: StockScore[] }) {
  return (
    <table className="w-full hairline-table">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Price</th>
          <th>Score</th>
          <th>Catalyst</th>
          <th>Technical</th>
          <th>Sentiment</th>
          <th>Setup</th>
        </tr>
      </thead>
      <tbody>
        {scores.map((s) => (
          <tr key={s.ticker} className="hover:bg-white/[0.02]">
            <td>
              <Link href={`/stocks/${s.ticker}`} className="font-mono font-medium">
                {s.ticker}
              </Link>
            </td>
            <td className="font-mono tabular-nums text-muted">${s.price.toFixed(2)}</td>
            <td>
              <ScoreValue value={s.overall_score} />
            </td>
            <td className="font-mono tabular-nums text-muted">{s.catalyst_score.toFixed(0)}</td>
            <td className="font-mono tabular-nums text-muted">{s.technical_score.toFixed(0)}</td>
            <td className="font-mono tabular-nums text-muted">{s.sentiment_score.toFixed(0)}</td>
            <td>
              <ActionBadge category={s.action_category} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
