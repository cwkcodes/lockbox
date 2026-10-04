import { Page } from "@/components/SiteHeader";

export const metadata = { title: "Methodology" };

const S = ({ id, title, children }: { id: string; title: string; children: React.ReactNode }) => (
  <section id={id} style={{ marginBottom: 26 }}><h2 style={{ fontSize: 17, margin: "0 0 8px", borderBottom: "1px solid var(--line)", paddingBottom: 4 }}>{title}</h2><div style={{ lineHeight: 1.6 }}>{children}</div></section>
);
const T = ({ head, rows }: { head: string[]; rows: string[][] }) => (
  <div className="panel" style={{ overflow: "auto", margin: "8px 0" }}><table className="data"><thead><tr>{head.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody></table></div>
);

const TOC = [
  ["principles", "Principles"], ["sources", "Source selection and authority"], ["pipeline", "Pipeline and data layers"], ["status", "Status normalisation"], ["taxonomy", "Technology taxonomy"],
  ["resolution", "Entity resolution and duplicates"], ["phases", "Phases and repowering"], ["coordinates", "Coordinates and accuracy"], ["conflicts", "Conflicts and preferred values"], ["calculated", "Calculated values"],
  ["confidence", "Confidence and completeness"], ["qa", "Quality assurance rules"], ["small", "Small-scale generation and privacy"], ["licensing", "Licensing and exports"], ["updates", "Update process"], ["limits", "Source-specific limitations"], ["gaps", "Known gaps in this build"],
];

export default function Methodology() {
  return (
    <Page title="Methodology" current="/methodology">
      <p className="muted" style={{ marginTop: -6 }}>How the database is built, how values are chosen, and where it is incomplete. Written for consultants and engineers who need to judge fitness for purpose.</p>
      <nav aria-label="Contents" className="panel" style={{ padding: 10, marginBottom: 20, columns: 2 }}>{TOC.map(([id, t]) => <div key={id}><a href={`#${id}`}>{t}</a></div>)}</nav>

      <S id="principles" title="Principles">
        <ul>
          <li><strong>Traceability.</strong> Every material value shown can be traced to a source record, with the source organisation, dataset, publication date, retrieval date, licence and (where the source has one) the original column and value.</li>
          <li><strong>No fabrication.</strong> Missing information is shown as <em>Unknown</em> or <em>Not publicly identified</em>. Turbine models, manufacturers, dimensions, dates, owners and positions are never inferred – for example a 3 MW average is never promoted to a “3 MW turbine”.</li>
          <li><strong>Disagreement is preserved.</strong> When sources conflict all observations are kept, one is marked preferred with a written reason, and the record shows “Alternative reported values available”.</li>
          <li><strong>Different quantities stay different.</strong> Installed, registered, accredited, contracted (CfD), TEC and export capacity are separate fields. Planning/consented envelope, reported values and as-built facts are separate. MW (power) and MWh (energy) are never mixed.</li>
          <li><strong>Not a complete register.</strong> Coverage is the most comprehensive <em>publicly verifiable</em> coverage reachable by the sources listed on the Data page; gaps are disclosed there.</li>
        </ul>
      </S>

      <S id="sources" title="Source selection and authority">
        <p>Sources were discovered and verified live (URL, format, publication date, licence) before ingestion; nothing relies on remembered endpoints. Each source has a tier:</p>
        <T head={["Tier", "Meaning", "Examples"]} rows={[["A", "Statutory decision, regulator record, network register or official government dataset", "DESNZ REPD, NESO TEC/Embedded, DNO Embedded Capacity Registers, CfD allocation results, The Crown Estate"], ["B", "Developer / operator / manufacturer primary source", "Project websites, planning-decision documents (none loaded yet)"], ["C", "Reputable industry publication or recognised open data", "—"], ["D", "Secondary media", "—"], ["E", "Community-maintained / open-source", "OpenStreetMap (adapter built; not run – see gaps)"]]} />
        <p>Tier does not decide conflicts blindly. For each field the preferred observation is chosen by (1) manual or research evidence, (2) source authority tier, (3) for locations the coordinate-accuracy class, (4) recency of the source value – and what the field represents is respected (a constructed-configuration developer page may supersede an older statutory application; a registered grid capacity is not compared with an installed capacity). The reason is stored with the choice.</p>
      </S>

      <S id="pipeline" title="Pipeline and data layers">
        <ol>
          <li><strong>Download</strong> with a declared User-Agent, per-host throttling, retries, caching and <code>robots.txt</code> checks; preference for published datasets/APIs over HTML.</li>
          <li><strong>Raw layer</strong> – the file and every row exactly as published (<code>raw.snapshot</code>, <code>raw.record</code>), with SHA-256, retrieval time and licence text. Old editions are retained, never overwritten.</li>
          <li><strong>Validate</strong> – structurally broken rows are quarantined (<code>raw.reject</code>) with a reason; one narrowly-defined, deterministic realignment is applied only when an exact signature matches and the repaired row then validates (see Source-specific limitations).</li>
          <li><strong>Normalised layer</strong> – every source mapped to one shape with units converted (kW→MW, m²→ha …), original values and per-field raw column references retained.</li>
          <li><strong>Canonical layer</strong> – entity resolution, provenance, conflicts, relationships, QA flags, completeness and confidence. Fully rebuildable from the normalised layer; asset IDs are stable because each asset is anchored to the identifier that first created it.</li>
          <li><strong>Change detection</strong> – a new edition is diffed against the previous one (new/removed projects, status, capacity, date, developer, connection changes) into a change log.</li>
        </ol>
      </S>

      <S id="status" title="Status normalisation">
        <p>Source wording is always stored beside the normalised status. Statuses used: operational, partially operational, commissioning, under construction, awaiting construction, consented, connection agreed, planning submitted, planning, CfD awarded, scoping, pre-planning, mothballed, decommissioned, withdrawn, refused, expired, cancelled, superseded, unknown, and the repowering variants.</p>
        <T head={["Source / wording", "Normalised status", "Note"]} rows={[
          ["REPD ‘Operational’", "Operational", ""], ["REPD ‘Under Construction’", "Under construction", ""], ["REPD ‘Awaiting Construction’ (planning permission / appeal / SoS granted)", "Awaiting construction", "Full REPD wording is kept"],
          ["REPD ‘Application Submitted’", "Planning submitted", ""], ["REPD ‘Application Refused’, ‘Appeal Refused’", "Refused", ""], ["REPD ‘Application Withdrawn’, ‘Appeal Withdrawn’", "Withdrawn", ""], ["REPD ‘Appeal Lodged’", "Planning", ""],
          ["REPD ‘Planning Permission Expired’", "Expired", ""], ["REPD ‘Abandoned’", "Cancelled", ""], ["REPD ‘Revised’", "Superseded", "A re-application exists; linked with a ‘supersedes’ relationship"], ["REPD ‘No Application Required’", "Unknown", "States nothing about construction stage"],
          ["ECR ‘Connected’ / ‘Accepted to connect’", "Operational / Connection agreed", "Connection-offer acceptance is not planning consent"], ["NESO ‘Built / Under Construction / Consents Approved / Awaiting Consents / Scoping’", "Operational / Under construction / Consented / Planning / Scoping", ""],
          ["Crown Estate ‘Active/In Operation, Under Construction, Consented, In Planning, Pre-planning Application’", "Operational … Pre-planning", "‘Government Support on Offer’ is left Unknown (a support stage, not a development stage)"], ["CfD results", "CfD awarded", "Allocation outcome only; says nothing about build stage and never overrides a concrete status"],
        ]} />
        <p>A project whose name carries a ‘repower’ marker and which is linked (by shared core name, technology and ≤3 km) to an existing asset is shown as <em>repowering proposed / consented / under construction</em>; the original status is retained.</p>
      </S>

      <S id="taxonomy" title="Technology taxonomy">
        <p>Onshore wind; offshore wind (fixed / floating / type unspecified – REPD does not state foundation type); solar PV; BESS; hydro; pumped-storage hydro; tidal stream; tidal range; wave; anaerobic digestion; biomass; landfill gas; sewage gas; geothermal; renewable CHP; and hybrid categories (wind/solar/BESS combinations – assigned only where one source record explicitly lists several technologies at one site; co-located projects registered separately are linked, not merged). An optional <em>Other low-carbon infrastructure</em> category holds energy from waste, advanced conversion, hydrogen, long-duration/compressed-air/flow storage and similar; <strong>energy from waste is not classed as renewable</strong>. Fossil gas, nuclear, demand and reactive-compensation entries in network registers are retained in the normalised layer but not promoted.</p>
      </S>

      <S id="resolution" title="Entity resolution and duplicates">
        <p>REPD is the national backbone: one canonical asset per REPD record. Records from other sources are linked to an asset only through a scored comparison; otherwise they become their own asset. Components and weights (re-normalised over the components available for a pair): name 25 %, location 25 %, technology 10 %, capacity 15 %, organisation 10 %, planning reference 10 %, date 5 %.</p>
        <ul>
          <li><strong>Never on name alone.</strong> An automatic link requires a total ≥ 0.80 <em>and</em> hard evidence (identical planning reference; co-location with consistent name/capacity; or near-identical name together with matching capacity). Scores of 0.55–0.80, or ambiguous best matches, go to a review queue.</li>
          <li><strong>Sibling guard.</strong> Names are compared on identity tokens after removing generic words and parenthetical aliases. Numbers, number-words, compass points, single letters and “phase/extension/repower” form a <em>variant signature</em>; different signatures (Hornsea 2 vs 3, Norfolk Vanguard East vs West, Whitelee vs Whitelee Extension, Ynni’r Lleuad 2 vs Ynni’r Lleuad) are never auto-linked. Subset names are not treated as identical.</li>
          <li><strong>Technology veto.</strong> Incompatible technologies are never linked; hybrid records match their component technologies with component capacities.</li>
          <li><strong>Positive-only soft evidence.</strong> Differing organisations or dates are not penalised (SPVs are renamed, operators change); only matches add support.</li>
          <li><strong>Polygons.</strong> A Crown Estate lease polygon matches a point by containment/proximity. For offshore pairs a <em>large distance is not treated as evidence against</em>: in the 4 Oct 2026 data several REPD offshore reference points lie 18–28 km from their lease polygon (e.g. Humber Gateway A, Dogger Bank C), so REPD offshore points are reference points, not array centroids.</li>
          <li><strong>Human decisions persist.</strong> Administrators can approve or reject a candidate; the decision is stored against stable identifiers and re-applied on every rebuild, with an audit-trail entry.</li>
        </ul>
        <p>Lease-only Crown Estate records that could not be linked remain separate <em>lease-area records</em> (filter “Record kind”); they carry no capacity and are excluded from project counts by default.</p>
      </S>

      <S id="phases" title="Phases and repowering">
        <p>Projects, phases and extensions are separate assets and are never auto-merged. Explicit REPD links (re-application references, storage co-location references) create ‘supersedes’ and ‘co-located with’ relationships. Where a name carries a phase/extension/repower marker and a base project with the same core name, technology and location (≤ 3 km) exists, a <em>heuristic</em> parent/repowering relationship is created, labelled “heuristic” and raised as a “potential repower duplicate” QA flag for review. Original and repowering generations are different assets; the map filter “Repowering” separates them.</p>
      </S>

      <S id="coordinates" title="Coordinates and accuracy">
        <T head={["Class", "Meaning"]} rows={[["exact published", "Coordinates published for the object itself (reserved for unit-level data)"], ["digitised from official planning drawing", "Extracted from a planning layout (reserved; none loaded)"], ["site reference", "A site grid reference in a register (REPD X/Y; DNO ‘where data is held’) – not a turbine/array position"], ["open-source mapped", "OpenStreetMap contributors (ODbL), supplementary only"], ["grid 1 km", "Published or privacy-masked to the centre of a 1 km square"], ["approximate", "Centroid/representative point of an area, or an indicative project location"]]} />
        <p>Positions are held in WGS84 (EPSG:4326) and British National Grid (EPSG:27700), transformed with PROJ at ingestion (the browser calculator uses a Helmert approximation, ±≈5 m). Out-of-range or implausible values are rejected, not guessed: eastings such as 3,862,265 are not BNG metres, and coordinates that transform outside UK waters are discarded (REPD points up to ~2.6° E in the North Sea are valid far-offshore sites even though they lie beyond the nominal BNG square). Observations from this dataset: all AR5/AR6 CfD offshore ‘Project Location’ OS references lie <em>on land</em> (grid connection/landfall), so they are not used as project positions; the AR7 offshore latitude/longitude is a “northerly extreme” point, labelled approximate.</p>
        <p><strong>Never</strong> a project centroid as a turbine coordinate: individual turbines exist only where a source gives them. None are verified in this build, so the Units tab says “Individual turbine coordinates not verified”.</p>
      </S>

      <S id="conflicts" title="Conflicts and preferred values">
        <p>Each observation (value, unit, source record, raw column and value, source date, kind) is stored in <code>field_provenance</code>. Where observations disagree (numbers by more than 1 %, or different text) the asset shows “Alternative reported values available”, and the Sources tab lists every value with the reason the preferred one was chosen. Generic–specific pairs (e.g. offshore wind vs floating offshore wind) are refinements, not conflicts; CfD “awarded” is context, not a competing development stage. Example genuine conflicts in current data: a project awarded a CfD in two rounds with different target dates and capacities.</p>
      </S>

      <S id="calculated" title="Calculated values">
        <p>Calculated values are always labelled with their expression and never mixed with published values: implied mean turbine rating (capacity ÷ reported turbine count), storage duration (MWh ÷ MW, only if both are published), swept area, MW/ha. Unit conversions (kW→MW, m²→ha) are normalisation, with the original value retained. Duration is shown as published or calculated, never silently.</p>
      </S>

      <S id="confidence" title="Confidence and completeness">
        <T head={["Rating", "Rule"]} rows={[["Verified", "Manual/research verification, or ≥ 3 independent tier-A sources agreeing with no material conflict"], ["High", "≥ 2 tier-A sources agreeing, or a tier-B primary source, with core fields present"], ["Medium", "A single tier-A source with name, status, capacity and coordinates"], ["Low", "Core fields missing, location only approximate, or an unresolved material conflict"]]} />
        <p><em>Completeness</em> is the percentage of expected fields for the technology that are populated (information availability, not truth) and is kept separate from confidence. Expected fields include, for wind, turbine count, manufacturer, model, hub height, rotor diameter, tip height and individual positions; for storage, MWh, duration, chemistry, supplier, PCS and integrator. Because most loaded sources do not state those fields, completeness is low by design and rises as primary sources are added.</p>
      </S>

      <S id="qa" title="Quality assurance rules">
        <p>Automated checks raise flags (viewable per asset and in the admin QA dashboard): missing/approximate coordinates; status conflicts; capacity discrepancy between sources (different quantities – informational); duplicate candidates; potential repower duplicates; turbine-count conflicts; model not verified; planning reference missing; old source (&gt;3 years); capacity arithmetic (turbines × rated MW vs capacity, &gt;15 %); unknown owner/operator; <strong>coordinates not on GB land</strong> and <strong>stated country contradicting the coordinates</strong> (this catches REPD errors such as Scottish farms keyed into the North Sea and Isle of Man schemes filed under England); capacity unit suspicion (MW vs kW); identical coordinates shared by unrelated projects; date-order inconsistency; operational-in-future; BESS duration inconsistency; tip height vs hub + rotor radius.</p>
      </S>

      <S id="small" title="Small-scale generation and privacy">
        <p>Domestic microgeneration is out of scope as point data. Network-register rows below 1 MW can carry customer names, addresses and postcodes: these stay in the raw layer; the public layer shows no name, address or postcode for such rows, uses a generated descriptive label, and rounds the location to the centre of a 1 km grid square. REPD addresses and postcodes are shown only for schemes of 1 MW or more. MPAN identifiers are never surfaced. Utility-scale/commercial records are kept distinct (scale filter).</p>
      </S>

      <S id="licensing" title="Licensing and exports">
        <p>Licence name, URL, attribution and redistribution/commercial notes are stored per source and shown on the Data page; attribution is displayed on the map and included in exports. Examples: REPD, CfD results and ONS boundaries – Open Government Licence v3.0; NESO – NESO Open Data Licence (attribution “Supported by National Energy SO Open Data”, commercial use permitted); The Crown Estate – GIS Open Data Licence v1.1 (mandatory attribution; no resale or direct commercial gain from supplying the data; not to be reproduced on a service providing the same or similar services as the Crown Estate portal) – so Crown Estate geometry is displayed with attribution but <strong>excluded from exports by default</strong> until a licence review is recorded. Sources whose licence text was not verified from the primary document are excluded from bulk export by default. Basemap providers have their own terms (see deployment notes).</p>
      </S>

      <S id="updates" title="Update process">
        <p>Adapters check <code>robots.txt</code> and throttle requests. Where a publisher’s robots.txt disallows automated access (NESO’s API host; every Opendatasoft DNO portal’s API/export paths; NGED’s portal, which also disallows Claude user-agents) the source is reported as “manual review required” and not fetched. An operator may (a) ingest a file they downloaded through the publisher’s own download button (<code>atlas-ingest ingest &lt;source&gt; --file …</code>; recorded as “manually supplied”), or (b) after reviewing the terms, explicitly override robots for one host (<code>ATLAS_ROBOTS_OVERRIDE</code>; recorded on the snapshot). Suggested cadences: REPD quarterly; NESO and DNO registers weekly to monthly; Crown Estate and CfD on publication; boundaries annually.</p>
      </S>

      <S id="limits" title="Source-specific limitations">
        <ul>
          <li><strong>REPD</strong> tracks projects over 150 kW; the minimum threshold was 1 MW until 2021, so sub-1 MW projects that went through planning earlier may be absent. “Operator (or Applicant)” is the operator once operational and the applicant before. X/Y is a site reference, not a turbine position. “Height of Turbines” does not say whether tip or hub height. “Offshore Wind Round” contains Excel date artefacts (01/01/1900 = Round 1 …), mapped and noted. Some coordinates are wrong (see QA).</li>
          <li><strong>NESO TEC / Embedded</strong>: capacity is cumulative contracted TEC (may include not-yet-connected capacity), there are no coordinates, and fossil/nuclear/demand entries are not promoted.</li>
          <li><strong>DNO ECRs</strong>: registered capacity ≠ installed capacity; locations may be 1 km resolution or redacted; at least one network’s 50 kW–1 MW file has column-shifted rows (an inserted postcode district) – these are realigned only when the exact signature matches and the realigned row validates, otherwise quarantined.</li>
          <li><strong>CfD results</strong> are allocation outcomes, not the LCCC contract register: contracts may be terminated, re-sized or re-named; capacity is contracted, not installed; strike prices are in 2012 prices (and 2024 where given).</li>
          <li><strong>Crown Estate</strong> polygons are lease/agreement areas, not turbine layouts or consented arrays; Scotland is Crown Estate Scotland (not loaded).</li>
          <li><strong>Planning data</strong>: an application may describe a maximum design envelope that differs from what was built; consented, reported and installed values are kept separate.</li>
          <li><strong>Ofgem</strong> scheme capacity (RO/REGO/FIT accreditation) can differ from physical capacity; station-level data was not obtainable here.</li>
        </ul>
      </S>

      <S id="gaps" title="Known gaps in this build">
        <p>Stated plainly, as of the 4 October 2026 build: REPD (quarterly extract, July 2026), CfD results (AR5–AR7a), Crown Estate wind-site agreements and ONS boundaries are loaded. <strong>Not loaded:</strong> NESO TEC/Embedded and the DNO Embedded Capacity Registers (publishers’ robots.txt disallows automated access; adapters and an operator-supplied-file route are built and tested on synthetic fixtures); SSEN ECR (HTTP 403); Ofgem RER/RO/REGO/FIT station data; Scottish Energy Consents, PINS and Welsh DNS/SIP registers; LCCC contract register; Crown Estate Scotland; OpenStreetMap (no permitted endpoint). Consequently grid, ownership, equipment (turbine model, hub/rotor/tip, BESS MWh, module/inverter) and individual-turbine positions are largely “not publicly identified”; the research queue lists what to look up first, in the order wind → solar → BESS → hydro → offshore. Planning-document extraction and manufacturer specification libraries are designed (schema, evidence documents, turbine-model library) but unpopulated.</p>
      </S>
    </Page>
  );
}
