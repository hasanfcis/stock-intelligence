import { notFound } from "next/navigation";
import { getStock } from "@/lib/api";
import { ActionBadge, ScoreValue } from "@/components/ScoreBadge";

export const dynamic = "force-dynamic";

export default async function StockPage({
  params,
}: {
  params: { ticker: string };
}) {
  const stock = await getStock(params.ticker);
  if (!stock) notFound();

  const { thesis_vs_price: tvp } = stock;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="font-mono text-2xl">{stock.ticker}</h1>
          <div className="text-sm text-muted mt-1">${stock.price.toFixed(2)}</div>
        </div>
        <div className="flex items-center gap-3">
          <ScoreValue value={stock.overall_score} />
          <ActionBadge category={stock.action_category} />
        </div>
      </div>

      <section className="grid grid-cols-3 gap-4">
        <ScoreBar label="Technical" value={stock.technical_score} />
        <ScoreBar label="Catalyst" value={stock.catalyst_score} />
        <ScoreBar label="Sentiment" value={stock.sentiment_score} />
      </section>

      <section>
        <h2 className="text-sm text-muted mb-3">Why today?</h2>
        <ul className="panel px-4 py-3 flex flex-col gap-2">
          {stock.why_today.map((reason, i) => (
            <li key={i} className="text-sm flex gap-2">
              <span className="text-muted">—</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-sm text-muted mb-3">Thesis vs. price</h2>
        <div className="panel px-4 py-3 grid grid-cols-4 gap-4">
          <Field label="Company" value={tvp.company_quality} />
          <Field label="Long-term thesis" value={tvp.long_term_thesis} />
          <Field label="Current price" value={tvp.price_state} />
          <Field label="Action" value={tvp.action} emphasize />
        </div>
      </section>

      {stock.entry && (
        <section>
          <h2 className="text-sm text-muted mb-3">Trade levels</h2>
          <div className="panel px-4 py-3 grid grid-cols-4 gap-4 font-mono">
            <Field label="Entry" value={`$${stock.entry[0].toFixed(2)}\u2013$${stock.entry[1].toFixed(2)}`} />
            <Field label="Stop" value={stock.stop ? `$${stock.stop.toFixed(2)}` : "\u2014"} />
            <Field
              label="Targets"
              value={stock.targets.length ? stock.targets.map((t) => `$${t.toFixed(2)}`).join(" / ") : "\u2014"}
            />
            <Field label="Risk/Reward" value={stock.risk_reward ? `1:${stock.risk_reward.toFixed(1)}` : "\u2014"} />
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm text-muted mb-3">Sources</h2>
        <ul className="panel px-4 py-3 flex flex-col gap-3">
          {stock.sources.length === 0 && (
            <li className="text-sm text-muted">No sourced catalysts today.</li>
          )}
          {stock.sources.map((s, i) => (
            <li key={i} className="text-sm">
              <a href={s.url} target="_blank" rel="noreferrer" className="text-amber hover:underline">
                {s.source_name}
              </a>
              <span className="text-muted"> — {s.summary}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="panel px-4 py-3">
      <div className="flex justify-between items-baseline mb-2">
        <span className="text-xs text-muted">{label}</span>
        <ScoreValue value={value} />
      </div>
      <div className="h-1 bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full bg-amber"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: string;
  emphasize?: boolean;
}) {
  return (
    <div>
      <div className="text-xs text-muted mb-1">{label}</div>
      <div className={`text-sm capitalize ${emphasize ? "text-amber font-medium" : ""}`}>{value}</div>
    </div>
  );
}
