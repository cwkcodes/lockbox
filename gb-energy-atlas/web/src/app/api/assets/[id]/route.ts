import { getAssetDetail } from "@/lib/queries";
import { apiError, json } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  if (!/^GBA-\d{7}$/.test(id)) return apiError(400, "asset id must look like GBA-0000001");
  const d = await getAssetDetail(id);
  return d ? json(d) : apiError(404, "asset not found");
}
