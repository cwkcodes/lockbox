import { NextRequest } from "next/server";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { apiError, filtersFrom } from "@/lib/api";
import { exportRows } from "@/lib/exportRows";
import { csvEscape } from "@/lib/format";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(req: NextRequest) {
  const { filters } = filtersFrom(req);
  const format = (req.nextUrl.searchParams.get("format") ?? "csv").toLowerCase();
  const stamp = new Date().toISOString().slice(0, 10);
  const result = await exportRows(filters);
  const { rows, columns, attribution, notes } = result;

  if (format === "csv") {
    const body = [columns.join(","), ...rows.map((r) => columns.map((c) => csvEscape(r[c])).join(","))].join("\r\n");
    return new Response("﻿" + body + "\r\n", { headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="gb-energy-atlas-${stamp}.csv"` } });
  }
  if (format === "xlsx") {
    const ExcelJS = (await import("exceljs")).default;
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet("Assets");
    ws.columns = columns.map((c) => ({ header: c, key: c, width: Math.min(40, Math.max(12, c.length + 2)) }));
    for (const r of rows) ws.addRow(Object.fromEntries(columns.map((c) => [c, r[c] instanceof Date ? (r[c] as Date).toISOString().slice(0, 10) : (typeof r[c] === "string" && /^[=+\-@]/.test(r[c] as string) ? `'${r[c]}` : r[c])])));
    ws.getRow(1).font = { bold: true }; ws.views = [{ state: "frozen", ySplit: 1 }]; ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: columns.length } };
    const readme = wb.addWorksheet("README – attribution & notes");
    readme.addRow(["GB Renewable Energy Atlas export", stamp]); readme.addRow([]);
    readme.addRow(["Attribution (must be retained)"]); attribution.forEach((a) => readme.addRow([a]));
    readme.addRow([]); readme.addRow(["Notes"]); notes.forEach((n) => readme.addRow([n])); readme.getColumn(1).width = 140;
    const buf = await wb.xlsx.writeBuffer();
    return new Response(new Uint8Array(buf as ArrayBuffer), { headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Content-Disposition": `attachment; filename="gb-energy-atlas-${stamp}.xlsx"` } });
  }
  if (format === "geojson" || format === "gpkg") {
    const geo = {
      type: "FeatureCollection", attribution, export_notes: notes,
      features: rows.filter((r) => r.lat !== null && r.lon !== null).map((r) => {
        const { lat, lon, ...props } = r;
        return { type: "Feature", geometry: { type: "Point", coordinates: [Number(lon), Number(lat)] }, properties: props };
      }),
    };
    if (format === "geojson") return new Response(JSON.stringify(geo), { headers: { "Content-Type": "application/geo+json", "Content-Disposition": `attachment; filename="gb-energy-atlas-${stamp}.geojson"` } });
    const ogr = process.env.OGR2OGR_PATH;
    if (!ogr) return apiError(501, "GeoPackage export needs GDAL: set OGR2OGR_PATH to the ogr2ogr binary (see docs/DEPLOYMENT.md). GeoJSON export is always available.");
    const dir = await mkdtemp(path.join(tmpdir(), "atlas-gpkg-"));
    try {
      await writeFile(path.join(dir, "in.geojson"), JSON.stringify({ ...geo, attribution: undefined, export_notes: undefined }));
      await new Promise<void>((resolve, reject) => {
        const p = spawn(ogr, ["-f", "GPKG", path.join(dir, "out.gpkg"), path.join(dir, "in.geojson"), "-nln", "assets", "-a_srs", "EPSG:4326"]);
        p.on("error", reject); p.on("exit", (c) => (c === 0 ? resolve() : reject(new Error(`ogr2ogr exited ${c}`))));
      });
      const buf = await readFile(path.join(dir, "out.gpkg"));
      return new Response(new Uint8Array(buf), { headers: { "Content-Type": "application/geopackage+sqlite3", "Content-Disposition": `attachment; filename="gb-energy-atlas-${stamp}.gpkg"`, "X-Attribution": attribution.join(" | ").slice(0, 900) } });
    } finally { await rm(dir, { recursive: true, force: true }); }
  }
  void query;
  return apiError(400, "format must be csv, xlsx, geojson or gpkg");
}
