# 08 — Business Model

Strategy: **breadth free, depth paid.** The free product must feel like Wikipedia — generous enough to become a habit and a link-share reflex (every shared map is an ad). Revenue comes from power users, education, and B2B data/API — not from gating exploration.

## 1. Tiers

| Tier | Price (indicative) | Gets |
|---|---|---|
| **Free** | $0 | Full catalogue, unlimited exploration, 2-layer overlay, Compare, timeline, 10 saved maps, PNG export with attribution, 25 AI queries/day |
| **Plus** (consumer) | $6/mo · $48/yr | Unlimited saved maps/collections, unlimited overlays, full Correlation Mode (free tier gets top-3 results as a teaser), PDF/SVG/hi-res export, offline packs, no export watermark (attribution footer stays — licensing), priority AI quota |
| **Pro** (analyst/creator) | $19/mo | Plus + bulk data downloads (CSV/GeoParquet), API access (Pro rate tier), embed without badge on personal sites, early datasets |
| **Education** | Free for verified teachers/students; site licence $1–2/student/yr for institutions | Plus features + lesson packs, classroom collections, quiz assignments, admin dashboard. Education is a distribution strategy as much as revenue — school habit → lifetime users |
| **University/Research** | $2–5k/yr dept licence | Pro seats + sub-national data packs + citation export + priority dataset requests |
| **Business** | from $500/mo | White-label embeds (no badge, custom style), domain-locked tokens, SLA API, custom datasets ingestion, SSO |
| **Government/NGO** | Custom | White-label instances, private data layers alongside the public catalogue, procurement-friendly contracting |

## 2. API subscriptions

Metered on top of Pro/Business: requests/month bands, tile-serving quota, webhooks. The API sells the same artefacts the product already produces (values JSON, tiles, GeoParquet), so marginal cost ≈ CDN egress. Position against: raw source wrangling (our value = one clean, joined, versioned, licensed catalogue).

## 3. Marketplace (Phase 4+)

Community/publisher datasets with rev-share (70/30), mandatory licence declaration, validation pipeline gate, and editorial review before public listing. Realistic expectation: this is a moat/ecosystem play, not a near-term revenue line.

## 4. Advertising

**No display ads.** They poison the "credible atlas" brand and the education market. The only acceptable sponsorship format: clearly-labelled *sponsored collections* from vetted institutions (e.g. a science museum sponsoring the volcano collection) — Phase 4 decision, default off.

## 5. White-label licensing

Newsrooms, textbooks publishers, museums, utilities: embedded StatMaps with custom branding/catalogue subsets. High-touch, high-margin; needs the embed SDK + domain-token infrastructure (already specced in 05-api) — sales motion starts Phase 3 once embeds are polished.

## 6. Unit economics sanity check

- Infra at scale ≈ $0.02–0.04/MAU/mo (03-architecture §8) — a 1–2% Plus conversion at $4/mo net covers infra ~5–10×. People (data team, eng) dominate costs; breakeven is a headcount question, not an infra question.
- AI quota design keeps the marginal free user's AI cost < $0.01/mo (cached artefacts) — the expensive features are exactly the paid ones.

## 7. Licensing constraints on monetisation (cross-ref 02-data §3)

CC BY sources: fine commercially with attribution (the non-removable footer). NC-licensed sources (WHO-direct, Ookla, SIPRI): either substituted with open equivalents or excluded from paid API redistribution — the `licences` table gates this automatically. ODbL (OSM-derived layers): share-alike applies to derivative *databases*; our OSM-derived tilesets remain openly available (as OSM norms expect) while proprietary value lives in the statistical catalogue and product layer. This posture is documented publicly — transparency here builds trust with the open-data community we depend on.
