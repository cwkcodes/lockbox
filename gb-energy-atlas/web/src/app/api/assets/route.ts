import { NextRequest } from "next/server";
import { query } from "@/lib/db";
import { filtersFrom, intParam, json, LIST_COLUMNS } from "@/lib/api";
import { SORTABLE } from "@/lib/filters";

export const dynamic = "force-dynamic";

/** GET /api/assets – server-side paginated, sortable, filterable list (same filters as tiles/stats/export). */
export async function GET(req: NextRequest) {
  const { where } = filtersFrom(req);
  const sp = req.nextUrl.searchParams;
  const page = intParam(req, "page", 1, 1, 100000);
  const pageSize = intParam(req, "pageSize", 50, 1, 500);
  const sortCol = SORTABLE[sp.get("sort") ?? "capacity"] ?? SORTABLE.capacity;
  const dir = sp.get("dir") === "asc" ? "ASC" : "DESC";
  const [rows, count] = await Promise.all([
    query(`SELECT ${LIST_COLUMNS} FROM atlas.asset_flat f WHERE ${where.sql} ORDER BY ${sortCol} ${dir} NULLS LAST, f.asset_id LIMIT ${pageSize} OFFSET ${(page - 1) * pageSize}`, where.params),
    query(`SELECT count(*)::int AS n FROM atlas.asset_flat f WHERE ${where.sql}`, where.params),
  ]);
  return json({ total: count[0].n, page, pageSize, items: rows });
}
