import { NextRequest } from "next/server";
import { apiError, json } from "@/lib/api";
import { getAssetDetail } from "@/lib/queries";

export const dynamic = "force-dynamic";

/** GET /api/compare?ids=GBA-1,GBA-2[,…up to 5] – side-by-side data with technology-specific rows chosen automatically. */
export async function GET(req: NextRequest) {
  const ids = (req.nextUrl.searchParams.get("ids") ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  if (ids.length < 2 || ids.length > 5 || !ids.every((i) => /^GBA-\d{7}$/.test(i))) return apiError(400, "provide 2–5 asset ids");
  const details = (await Promise.all(ids.map(getAssetDetail))).filter(Boolean);
  const families = new Set(details.map((d) => String((d as Record<string, unknown>).family)));
  return json({ families: [...families], assets: details });
}
