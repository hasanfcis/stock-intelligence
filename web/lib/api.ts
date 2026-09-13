import {
  CatalystFeedItem,
  DailyReport,
  HistoryResponse,
  StockScore,
  UniverseResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Every call is best-effort: the dashboard should render its empty state
 * rather than crash when the backend hasn't run a report yet (a fresh
 * clone with no /reports/run call made will 404 on /reports/latest). */
async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getLatestReport(): Promise<DailyReport | null> {
  return getJson<DailyReport>("/reports/latest");
}

export async function getStock(ticker: string): Promise<StockScore | null> {
  return getJson<StockScore>(`/stocks/${ticker}`);
}

export async function getCatalystFeed(): Promise<CatalystFeedItem[]> {
  const res = await getJson<{ items: CatalystFeedItem[] }>("/catalysts");
  return res?.items ?? [];
}

export async function getHistory(): Promise<HistoryResponse> {
  const res = await getJson<HistoryResponse>("/history");
  return res ?? { items: [], buckets: [], note: "Could not reach the API." };
}

export async function getUniverse(): Promise<UniverseResponse | null> {
  return getJson<UniverseResponse>("/universe");
}

export async function runReport(tickers?: string[]): Promise<DailyReport | null> {
  try {
    const res = await fetch(`${API_URL}/reports/run`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ tickers: tickers ?? null }),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as DailyReport;
  } catch {
    return null;
  }
}
