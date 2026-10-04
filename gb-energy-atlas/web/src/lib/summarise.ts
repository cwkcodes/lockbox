/** Capacity / count summary shared by the proximity tools. */
export function summarise(items: Record<string, unknown>[]) {
  const by: Record<string, { n: number; mw: number }> = {};
  let op = 0, pipe = 0, turbines = 0, bessMw = 0, bessMwh = 0;
  for (const i of items) {
    const fam = String(i.family), mw = Number(i.installed_capacity_mw ?? 0);
    by[fam] ??= { n: 0, mw: 0 }; by[fam].n++; by[fam].mw += mw;
    if (i.stage_group === "operational") op += mw; if (i.stage_group === "pipeline") pipe += mw;
    if (fam === "wind") turbines += Number(i.turbine_count ?? 0);
    if (fam === "storage") { bessMw += mw; bessMwh += Number(i.storage_capacity_mwh ?? 0); }
  }
  return { count: items.length, byFamily: by, operational_mw: op, pipeline_mw: pipe, turbines_reported: turbines, storage_mw: bessMw, storage_mwh: bessMwh };
}
