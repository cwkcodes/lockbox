/** Technology shapes + status patterns: shared by canvas map icons, the legend and list glyphs (single source of truth). */
export type Pattern = "solid" | "half" | "outline" | "muted" | "cross";

const pts = (cx: number, cy: number, r: number, n: number, rot = -Math.PI / 2): string =>
  Array.from({ length: n }, (_, i) => `${i ? "L" : "M"}${(cx + r * Math.cos(rot + (2 * Math.PI * i) / n)).toFixed(2)},${(cy + r * Math.sin(rot + (2 * Math.PI * i) / n)).toFixed(2)}`).join("") + "Z";

/** SVG path (also valid for Path2D) for a shape centred on (cx, cy) with nominal radius r. */
export function shapePath(shape: string, cx: number, cy: number, r: number): string {
  switch (shape) {
    case "square": { const a = r * 0.86; return `M${cx - a},${cy - a}h${2 * a}v${2 * a}h${-2 * a}Z`; }
    case "diamond": return `M${cx},${cy - r * 1.1}L${cx + r * 1.1},${cy}L${cx},${cy + r * 1.1}L${cx - r * 1.1},${cy}Z`;
    case "triangle": return `M${cx},${cy - r * 1.05}L${cx + r * 1.05},${cy + r * 0.8}L${cx - r * 1.05},${cy + r * 0.8}Z`;
    case "triangle-down": return `M${cx},${cy + r * 1.05}L${cx + r * 1.05},${cy - r * 0.8}L${cx - r * 1.05},${cy - r * 0.8}Z`;
    case "hexagon": return pts(cx, cy, r * 1.05, 6, 0);
    case "pentagon": return pts(cx, cy, r * 1.05, 5);
    case "octagon": return pts(cx, cy, r * 1.02, 8, Math.PI / 8);
    case "star": {
      const o = r * 1.2, i = r * 0.52;
      return Array.from({ length: 10 }, (_, k) => { const rad = k % 2 ? i : o; const a = -Math.PI / 2 + (Math.PI * k) / 5; return `${k ? "L" : "M"}${(cx + rad * Math.cos(a)).toFixed(2)},${(cy + rad * Math.sin(a)).toFixed(2)}`; }).join("") + "Z";
    }
    case "cross": { const w = r * 0.42, l = r * 1.05; return `M${cx - w},${cy - l}h${2 * w}v${l - w}h${l - w}v${2 * w}h${-(l - w)}v${l - w}h${-2 * w}v${-(l - w)}h${-(l - w)}v${-2 * w}h${l - w}Z`; }
    case "ring": return `M${cx - r},${cy}a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0ZM${cx - r * 0.45},${cy}a${r * 0.45},${r * 0.45} 0 1,1 ${r * 0.9},0a${r * 0.45},${r * 0.45} 0 1,1 ${-r * 0.9},0Z`;
    default: return `M${cx - r},${cy}a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0Z`;
  }
}

export const MUTED = "#8593a6";

/** Draw one icon (technology shape × status pattern) into a canvas context. */
export function drawIcon(ctx: CanvasRenderingContext2D, size: number, shape: string, colour: string, pattern: Pattern, dark: boolean): void {
  const c = size / 2, r = size * 0.34;
  const path = new Path2D(shapePath(shape, c, c, r));
  ctx.clearRect(0, 0, size, size);
  ctx.lineJoin = "round";
  const halo = dark ? "rgba(8,17,30,.9)" : "rgba(255,255,255,.95)";
  const fill = pattern === "muted" ? MUTED : colour;
  if (pattern !== "muted") { ctx.lineWidth = size * 0.17; ctx.strokeStyle = halo; ctx.stroke(path); }
  ctx.globalAlpha = pattern === "solid" ? 1 : pattern === "half" ? 0.5 : pattern === "muted" ? 0.6 : 0.12;
  ctx.fillStyle = fill; ctx.fill(path, shape === "ring" ? "evenodd" : "nonzero");
  ctx.globalAlpha = 1;
  if (pattern !== "solid" && pattern !== "muted") { ctx.lineWidth = size * 0.085; ctx.strokeStyle = colour; ctx.stroke(path); }
  if (pattern === "cross") { // strike-through: not colour-dependent
    ctx.lineWidth = size * 0.08; ctx.strokeStyle = colour; ctx.beginPath(); ctx.moveTo(c - r, c - r); ctx.lineTo(c + r, c + r); ctx.moveTo(c + r, c - r); ctx.lineTo(c - r, c + r); ctx.stroke();
  }
}
