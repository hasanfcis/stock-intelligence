import { getCatalystFeed } from "@/lib/api";
import { EmptyState } from "@/components/EmptyState";

export const dynamic = "force-dynamic";

export default async function CatalystsPage() {
  const items = await getCatalystFeed();

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-lg">Catalyst feed</h1>

      {items.length === 0 ? (
        <EmptyState
          title="No catalysts yet"
          detail="Run the pipeline to populate today's catalyst feed across your universe."
        />
      ) : (
        <ul className="panel divide-y divide-border">
          {items.map((item, i) => (
            <li key={i} className="px-4 py-3 flex gap-4">
              <div className="w-16 shrink-0 font-mono text-xs text-muted pt-0.5">
                {new Date(item.published_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
              <div>
                <div className="text-sm">
                  <span className="font-mono font-medium">{item.ticker}</span>
                  <span className="text-muted"> — {item.summary}</span>
                </div>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-amber hover:underline"
                >
                  {item.source_name}
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
