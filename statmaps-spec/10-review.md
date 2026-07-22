# 10 — Stretch Goals & Critical Design Review

## 1. Stretch goals (beyond the roadmap items already scheduled)

| Idea | Assessment |
|---|---|
| **Discover Mode** | Scheduled (Phase 3). Daily "tonight's fascinating maps" feed — curated seeds + AI ranking by novelty/engagement. The retention feature. |
| **AI Map Stories** | Scheduled (Phase 4). Scroll-driven narrative: camera moves + layer changes + timeline sync per chapter (a `story` = ordered list of map states + prose). AI drafts, humans edit — history content has too much reputational downside for unreviewed generation. |
| **Correlation auto-discovery** | Extension of the engine: nightly scan surfaces *new* statistically interesting pairs (novelty-ranked, FDR-controlled) into an editorial review queue → Discover feed. "The machine found something odd this week" is unique, defensible content. |
| **Live event overlays** | Quakes/fires Phase 2; flights/shipping/weather-radar Phase 4 (licensing for flight data — OpenSky is research-only ⚠️ — needs commercial ADS-B deal). |
| **Community datasets** | Phase 4 with the validation pipeline as the gate. The hard part is trust/liability, not tech — see risks below. |
| **Multiplayer exploration** | CRDT-shared map state (Yjs) — technically cheap because all state is already one serialisable object (01-product §2.8). Classroom use case makes it an Education-tier feature, not a gimmick. |
| **Lesson packs & quizzes** | Phase 3, revenue-attached. |
| **AR mode** | Spike-only until someone shows a use that beats the phone map. Highest cost/lowest evidence item on the list. |
| **3D globe** | Cheap now (MapLibre globe projection) — Phase 3. |
| **Custom dashboards** | Pro/Business tier: pinned map grid + stat tiles. Post-Phase-4; dashboards drift away from "the map is the interface" and need a strong B2B pull signal first. |
| **Dataset version history & diffs** | Already structural (04-database §6) — expose in UI Phase 3; analysts love it, it's nearly free. |
| **Data confidence scores** | In the model from day one (`datasets.confidence` + coverage %); UI treatment shipped Phase 1 (provenance panel). |
| **Plugin architecture** | Phase 4+, sandboxed iframes with typed postMessage; never third-party code in the map's WebGL context. Real ecosystems need scale first — don't build the marketplace before the market. |

## 2. Critical review — weaknesses, risks, and what we changed because of them

An honest red-team of this spec. Items marked ✅ already shaped the design above; items marked ⚠️ are open risks to manage.

### 2.1 Product risks

1. **"Interesting" ≠ "retained".** The catalogue is a toy without a reason to return. ✅ Mitigated by design: Discover feed, quizzes, live layers, correlation-of-the-week — but this remains the existential product risk. The Phase 1 exit criterion (D7 ≥ 15%) is the kill-or-continue gate; do not scale the data team before the loop retains.
2. **Breadth trap.** "Thousands of datasets" invites a shallow, stale catalogue that erodes trust ("this anime map is nonsense"). ✅ Mitigations: confidence scores + coverage badges displayed honestly; the Weird & Fun category explicitly labelled lower-confidence; demand-signal-driven backlog (zero-result search logging) instead of vanity breadth. ⚠️ Residual: the data team is a permanent editorial operation — budget it (2 FTE at launch, growing), or the product rots.
3. **Overlay legibility.** "Unlimited overlays" produces mud. ✅ Mitigated: hard UX guidance (2 choropleths max via multiply-blend, warnings beyond), Compare mode and Correlation Mode as the sanctioned answers to "I want to relate these".

### 2.2 Licensing & legal (the most underrated risk category)

4. **NC/ND/share-alike contamination.** One carelessly-ingested NC dataset in the paid API is a legal problem. ✅ Mitigated structurally: machine-readable licence gates on every dataset enforced by export/API code paths (04-database §2), substitution list for problem sources (02-data §3). ⚠️ Residual: needs a real legal review pass pre-launch and periodic audit; assign an owner.
5. **Disputed borders & sensitive categories** (Kashmir, Taiwan, Israel/Palestine; ethnicity/religion layers). ✅ Mitigated: `disputed_variant` geometry support, "boundaries approximate/contested" framing on historical layers, reviewed templates for AI on contested topics. ⚠️ Residual: app-store and per-country legal exposure (India's map law, China availability) — accept limited availability in some jurisdictions rather than forking truth; write the policy down before launch, not after the first incident.
6. **Brand POI data** (Starbucks, McDonald's). ✅ Solved by using OSM/Overture brand-tagged POIs instead of scraping. Completeness varies by country — show coverage honestly.
7. **ODbL share-alike anxiety.** ✅ Posture defined (08-business §7): OSM-derived tilesets stay open; proprietary value lives elsewhere. This is also community-strategically correct — we depend on the open-data ecosystem's goodwill.

### 2.3 Technical risks & bottlenecks

8. **Correlation engine embarrassment risk** — one viral screenshot of a dumb correlation presented credulously could brand the whole product as junk science. ✅ Heaviest-engineered mitigation in the spec: FDR correction, confounder screens, novelty ranking, spurious tier, non-causal language templates (06-ai §4.4). ⚠️ Residual: methodology needs an external statistician review before v1 ships. Cheap insurance — buy it.
9. **AI cost blowout.** ✅ Mitigated: pre-generation-first architecture, response/prompt caching, tiered quotas, degradation-to-cached mode instead of outage. The design goal that AI *manipulates precomputed data* rather than generating content per-request is the structural cost control.
10. **Tile/values fan-out at viral moments.** ✅ Structurally handled: everything on the render path is CDN-served immutable artefacts; a Reddit hug hits Cloudflare, not the origin. ⚠️ Residual: dynamic endpoints (Martin tiles, live layers, search) need the load-test discipline in 07-performance §7.
11. **Timeline + historical geometry complexity.** Temporal geometry versioning (04-database §1) is the most intricate part of the schema, and historical border data is genuinely poor. ✅ Mitigated: uniform valid_from/valid_to model, era-bucketed pre-built tilesets, "approximate" framing. ⚠️ Residual: scope discipline — historical mode ships Phase 3, resist pulling it earlier; it can consume the team.
12. **Two-language backend (TS + Python).** A real cost (two toolchains, two deploys). Accepted deliberately: the alternative — statistics in Node or product APIs in Python — is worse on both sides. Boundary is clean (Node = product surface, Python = numbers) and OpenAPI-typed.
13. **Postgres as the everything-box** (PostGIS + Timescale + pgvector). ✅ Right call at this scale; the pre-planned escape hatches are: analytics already offloaded to ClickHouse, hot path already off Postgres, vectors trivially movable. Tripwire for revisiting: sustained ingest lock contention or > 5 TB working set.
14. **Sub-national data explosion** (row counts, tile sizes, correlation combinatorics at ADM1/ADM2). ✅ Deferred by principle #4 (country-first); when it comes: Timescale compression, per-country tilesets, correlation scoped per-country-cluster. Don't pre-build for it.
15. **Search quality across 3k+ oddly-named datasets.** Lexical search alone will miss "money" → GDP. ✅ Mitigated: synonym curation + embedding-blended ranking (Phase 3) + zero-result AI rescue. This needs a permanent quality feedback loop (log failed searches → weekly triage).

### 2.4 Business risks

16. **Free tier too generous / too stingy** is a live tuning problem; the tier boundaries in 08-business are hypotheses. ✅ Instrumentation (PostHog funnels on every gate) specified so pricing iterates on data.
17. **Education sales cycles are slow.** Treat education as distribution first (free teacher tier immediately), institutional revenue later.
18. **Data-source rug-pulls** (APIs closing, licence changes — it happens: Twitter, Reddit, IEA). ✅ Mitigated: raw-zone archival of every ingest (we keep what we lawfully obtained), multi-source substitution table, version pinning. ⚠️ Residual: monitor licence pages of top-20 sources quarterly.

### 2.5 Verdict

The design is sound and deliberately boring where it should be (CDN-first delivery, Postgres-centred, one rendering trick — feature-state choropleths — doing most of the work). The three bets that must pay: **(1)** the discovery loop retains consumers, **(2)** the correlation engine is credible enough to be the brand, **(3)** the data operation stays funded as an editorial function. Everything else in this spec is execution.

**Recommended immediate next steps:**
1. Build the walking skeleton (Phase 1, weeks 1–6): boundary tiles + World Bank pipeline + MapLibre feature-state choropleth + search — the riskiest integrations, end to end.
2. Commission the external statistical review of the correlation methodology in parallel.
3. Run the licence audit on the launch catalogue before public beta.
