// frontend/app/[sport]/league/[id]/opengraph-image.tsx
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "WaiverEdge — your waiver wire moves this week";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

type Rec = {
  add_name: string;
  add_position: string;
  marginal: number;
  drop_name?: string | null;
  locked?: boolean;
};

type LockedRec = { locked: true; add_position: string };

async function fetchRecs(
  id: string,
): Promise<{ week: { start: string; end: string }; recs: Rec[] } | null> {
  const base =
    process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  try {
    const res = await fetch(`${base}/api/leagues/${id}/recs`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const data = await res.json();
    const recs: Rec[] = (data.recommendations ?? [])
      .slice(0, 3)
      .map((r: Rec | LockedRec, i: number) =>
        "locked" in r
          ? { add_name: "Unlock on Pro", add_position: r.add_position, marginal: 0, drop_name: null, locked: true }
          : { add_name: r.add_name, add_position: r.add_position, marginal: r.marginal, drop_name: r.drop_name ?? null, locked: false },
      );
    return { week: data.week, recs };
  } catch {
    return null;
  }
}

export default async function Image({
  params,
}: {
  params: { id: string; sport: string };
}) {
  const data = await fetchRecs(params.id);

  const week =
    data?.week
      ? `Week of ${data.week.start} – ${data.week.end}`
      : "Waiver Wire";

  const rows: Rec[] = data?.recs ?? [];

  return new ImageResponse(
    (
      <div
        style={{
          width: 1200,
          height: 630,
          background: "#0d0d0f",
          display: "flex",
          flexDirection: "column",
          padding: "56px 72px",
          fontFamily: "sans-serif",
        }}
      >
        {/* Wordmark */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 36,
          }}
        >
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: "#22c55e",
            }}
          />
          <span
            style={{
              color: "#22c55e",
              fontSize: 20,
              fontWeight: 700,
              letterSpacing: "0.05em",
              textTransform: "uppercase",
            }}
          >
            WaiverEdge
          </span>
        </div>

        {/* Title */}
        <div
          style={{
            color: "#f3f4f6",
            fontSize: 44,
            fontWeight: 800,
            lineHeight: 1.15,
            marginBottom: 8,
          }}
        >
          Your Moves
        </div>
        <div
          style={{
            color: "#6b7280",
            fontSize: 22,
            fontWeight: 400,
            marginBottom: 40,
          }}
        >
          {week}
        </div>

        {/* Rec rows */}
        {rows.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {rows.map((r, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 20,
                  background: "#18181b",
                  borderRadius: 14,
                  padding: "18px 28px",
                }}
              >
                {!r.locked && (
                  <span
                    style={{
                      color: "#22c55e",
                      fontSize: 28,
                      fontWeight: 800,
                      minWidth: 72,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {r.marginal >= 0 ? "+" : ""}
                    {r.marginal.toFixed(1)}
                  </span>
                )}
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span
                    style={{
                      color: r.locked ? "#6b7280" : "#f3f4f6",
                      fontSize: 26,
                      fontWeight: 700,
                    }}
                  >
                    {r.add_name}
                  </span>
                  {!r.locked && (
                    <span style={{ color: "#6b7280", fontSize: 18 }}>
                      {r.add_position}
                      {r.drop_name ? ` · drop ${r.drop_name}` : ""}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div
            style={{
              color: "#6b7280",
              fontSize: 28,
              marginTop: 24,
            }}
          >
            No waiver moves this week
          </div>
        )}

        {/* Watermark */}
        <div
          style={{
            position: "absolute",
            bottom: 48,
            right: 72,
            color: "#374151",
            fontSize: 18,
            fontWeight: 600,
            letterSpacing: "0.03em",
          }}
        >
          waiveredge.app
        </div>
      </div>
    ),
    { ...size },
  );
}
