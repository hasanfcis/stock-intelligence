import { ActionCategory } from "@/lib/types";

const ACTION_STYLES: Record<ActionCategory, string> = {
  "Strong Buy Setup": "text-gain border-gain/40 bg-gain/10",
  Watch: "text-amber border-amber/40 bg-amber/10",
  Neutral: "text-muted border-border bg-white/5",
  "Avoid / Sell": "text-loss border-loss/40 bg-loss/10",
};

export function ActionBadge({ category }: { category: ActionCategory }) {
  return (
    <span
      className={`inline-block text-xs font-mono px-2 py-0.5 rounded-sm border ${ACTION_STYLES[category]}`}
    >
      {category}
    </span>
  );
}

export function ScoreValue({ value }: { value: number }) {
  const color = value >= 80 ? "text-gain" : value >= 60 ? "text-amber" : value >= 40 ? "text-ink" : "text-loss";
  return <span className={`font-mono tabular-nums ${color}`}>{value.toFixed(0)}</span>;
}
