# Completeness review

Generated 2026-10-04 23:15 UTC from the loaded data. Findings are **leads for investigation**, not conclusions: an unmatched record may be a different project, a naming difference or genuinely missing from the other source.
## 1. Source coverage and cross-checks
| Source | State | Records loaded | Linked to another source's asset | Created its own asset |
|---|---|---|---|---|
| cfd_results | current | 427 | 199 | 228 |
| crown_estate_scotland | restricted | 0 | 0 | 0 |
| crown_estate_wind_sites | current | 72 | 22 | 50 |
| enwl_ecr_1mw | manual_review_required | 0 | 0 | 0 |
| enwl_ecr_lt1mw | manual_review_required | 0 | 0 | 0 |
| lccc_cfd | restricted | 0 | 0 | 0 |
| neso_embedded | manual_review_required | 0 | 0 | 0 |
| neso_tec | manual_review_required | 0 | 0 | 0 |
| nged_ecr | manual_review_required | 0 | 0 | 0 |
| npg_ecr_1mw | manual_review_required | 0 | 0 | 0 |
| npg_ecr_lt1mw | manual_review_required | 0 | 0 | 0 |
| ofgem_rer | source_unavailable | 0 | 0 | 0 |
| ons_lad | current | 361 | 0 | 0 |
| pins_nsip | manual_review_required | 0 | 0 | 0 |
| repd | current | 14657 | 0 | 14657 |
| scottish_energy_consents | manual_review_required | 0 | 0 | 0 |
| spen_ecr_1mw | manual_review_required | 0 | 0 | 0 |
| spen_ecr_50kw | manual_review_required | 0 | 0 | 0 |
| ssen_ecr | restricted | 0 | 0 | 0 |
| ukpn_ecr_1mw | manual_review_required | 0 | 0 | 0 |
| ukpn_ecr_lt1mw | manual_review_required | 0 | 0 | 0 |
| welsh_infrastructure | source_unavailable | 0 | 0 | 0 |
| osm_overpass | source_unavailable | 0 | 0 | 0 |

**Cross-checks that cannot be performed because the source is not loaded:** `crown_estate_scotland`, `enwl_ecr_1mw`, `enwl_ecr_lt1mw`, `lccc_cfd`, `neso_embedded`, `neso_tec`, `nged_ecr`, `npg_ecr_1mw`, `npg_ecr_lt1mw`, `ofgem_rer`, `pins_nsip`, `scottish_energy_consents`, `spen_ecr_1mw`, `spen_ecr_50kw`, `ssen_ecr`, `ukpn_ecr_1mw`, `ukpn_ecr_lt1mw`, `welsh_infrastructure`, `osm_overpass`. In particular: REPD ↔ ECR/TEC comparisons (projects missing from either), Ofgem ↔ REPD, and planning-register ↔ REPD need those sources (see `docs/SOURCE_CATALOGUE.md` §2 for why and how to load them).

## 2. Projects found only outside REPD (potential gaps in REPD, or unmatched records)
Largest first. CfD awards that never reached REPD are expected for early-stage projects; large operational ones deserve a manual check.

| Asset | Name | Technology | Status | MW | Source | Country |
|---|---|---|---|---|---|---|
| GBA-0014830 | Dogger Bank South East CfD Unit A | wind_offshore | cfd_awarded | 1500 | cfd_results | England |
| GBA-0014831 | Dogger Bank South West CfD Unit A | wind_offshore | cfd_awarded | 1500 | cfd_results | England |
| GBA-0014829 | Berwick Bank Phase B | wind_offshore | cfd_awarded | 1380 | cfd_results | Scotland |
| GBA-0014832 | Norfolk Vanguard East CFD Unit A | wind_offshore | cfd_awarded | 1380 | cfd_results | England |
| GBA-0014835 | Norfolk Vanguard West CFD Unit A | wind_offshore | cfd_awarded | 1380 | cfd_results | England |
| GBA-0014827 | East Anglia Two, Phase 1 | wind_offshore | cfd_awarded | 963.07 | cfd_results | England |
| GBA-0014828 | Awel y Môr Offshore Wind Farm A | wind_offshore | cfd_awarded | 775 | cfd_results | Wales |
| GBA-0014815 | Green Volt Offshore Windfarm (GV01) | wind_offshore_floating | cfd_awarded | 400 | cfd_results | Scotland |
| GBA-0014824 | Hornsea Project Three Offshore Wind Farm AR6 A | wind_offshore | cfd_awarded | 360 | cfd_results | England |
| GBA-0014825 | Hornsea Project Three Offshore Wind Farm AR6 C | wind_offshore | cfd_awarded | 360 | cfd_results | England |
| GBA-0014826 | Hornsea Project Three Offshore Wind Farm AR6 B | wind_offshore | cfd_awarded | 360 | cfd_results | England |
| GBA-0014788 | Longfield Solar Energy Farm | solar_pv | cfd_awarded | 299 | cfd_results | England |
| GBA-0014715 | Viking Wind Farm AR5 | wind_onshore | cfd_awarded | 223.6 | cfd_results | Scotland |
| GBA-0014928 | West Burton Solar Project - AR7 - Site 3 | solar_pv | cfd_awarded | 207.3 | cfd_results | England |
| GBA-0014845 | SANQUHAR II COMMUNITY WIND FARM BMU 2 | wind_onshore | cfd_awarded | 186 | cfd_results | Scotland |
| GBA-0014927 | West Burton Solar Project - AR7 - Site 2 | solar_pv | cfd_awarded | 182.6 | cfd_results | England |
| GBA-0014820 | Inch Cape A | wind_offshore | cfd_awarded | 177.41 | cfd_results | Scotland |
| GBA-0014823 | EA3B | wind_offshore | cfd_awarded | 158.9 | cfd_results | England |
| GBA-0014813 | Cloiche Wind Farm | wind_onshore | cfd_awarded | 130.5 | cfd_results | Scotland |
| GBA-0014842 | Glendye Wind Farm | wind_onshore | cfd_awarded | 124.8 | cfd_results | Scotland |
| GBA-0014838 | Erebus | wind_offshore_floating | cfd_awarded | 100 | cfd_results | Wales |
| GBA-0014784 | Little Crow Solar Park | solar_pv | cfd_awarded | 99.9 | cfd_results | England |
| GBA-0014926 | West Burton Solar Project - AR7 - Site 1 | solar_pv | cfd_awarded | 90.1 | cfd_results | England |
| GBA-0014833 | Norfolk Vanguard East CFD Unit B | wind_offshore | cfd_awarded | 90 | cfd_results | England |
| GBA-0014836 | Norfolk Vanguard West CFD Unit B | wind_offshore | cfd_awarded | 90 | cfd_results | England |
| GBA-0014821 | Inch Cape B | wind_offshore | cfd_awarded | 88.7 | cfd_results | Scotland |
| GBA-0014846 | SANQUHAR II COMMUNITY WIND FARM BMU1 | wind_onshore | cfd_awarded | 83.4 | cfd_results | Scotland |
| GBA-0014834 | Norfolk Vanguard East CFD Unit C | wind_offshore | cfd_awarded | 75 | cfd_results | England |
| GBA-0014837 | Norfolk Vanguard West CFD Unit C | wind_offshore | cfd_awarded | 75 | cfd_results | England |
| GBA-0014822 | Moray Offshore Windfarm (West) String 9 | wind_offshore | cfd_awarded | 73.5 | cfd_results | Scotland |
| GBA-0014809 | Corriegarth 2 Wind Farm Limited | wind_onshore | cfd_awarded | 66.19 | cfd_results | Scotland |
| GBA-0014716 | Enso Green Holdings I Limited | solar_pv | cfd_awarded | 57 | cfd_results | England |
| GBA-0014708 | ENERGYFARM UK MARGREE LLP | wind_onshore | cfd_awarded | 50 | cfd_results | Scotland |
| GBA-0014786 | Horton Solar Farm | solar_pv | cfd_awarded | 50 | cfd_results | England |
| GBA-0014791 | NEXTPOWER SPV 14 LIMITED | solar_pv | cfd_awarded | 50 | cfd_results | England |
| GBA-0014717 | Gonerby Solar | solar_pv | cfd_awarded | 49.99 | cfd_results | England |
| GBA-0014754 | CLUMP FARM SOLAR LIMITED | solar_pv | cfd_awarded | 49.99 | cfd_results | England |
| GBA-0014777 | Sheepwash Solar Farm | solar_pv | cfd_awarded | 49.99 | cfd_results | England |
| GBA-0014901 | Garendon Solar Plant | solar_pv | cfd_awarded | 49.99 | cfd_results | England |
| GBA-0014718 | King's Lynn | solar_pv | cfd_awarded | 49.9 | cfd_results | England |

## 3. Offshore lease areas not linked to a REPD project
A lease is linked only with hard evidence (the REPD point inside the polygon, or an identifier). Where the closest-named REPD project is shown as a lead it was **not** linked – e.g. its point lies far outside the polygon, or the names differ by a phase letter – and needs human review.

| Asset | Lease area | Status | Closest-named REPD project (lead, not linked) |
|---|---|---|---|
| GBA-0014680 | Blyth Demo Phase 1 | operational |  |
| GBA-0014673 | Dogger Bank A | under_construction | GBA-0002046 Dogger Bank C (was Teesside A) (REPD 2517, 1200 MW, 56 km away) |
| GBA-0014674 | Dogger Bank B | under_construction | GBA-0007576 Dogger Bank South East (REPD 11109, 1500 MW, no coordinates) |
| GBA-0014671 | Dogger Bank C | under_construction | GBA-0002046 Dogger Bank C (was Teesside A) (REPD 2517, 1200 MW, 37 km away) |
| GBA-0014663 | Dudgeon | operational | GBA-0002061 Dudgeon East (REPD 2538, 402 MW, 54 km away) |
| GBA-0014683 | Dudgeon Extension | planning | GBA-0005855 Dudgeon Extension Project (REPD 7692, 402 MW, 22 km away) |
| GBA-0014678 | East Anglia ONE | operational | GBA-0002007 East Anglia 3 (EA 3) (REPD 2470, 1400 MW, 24 km away) |
| GBA-0014699 | East Anglia ONE North | consented | GBA-0002008 East Anglia 1 North (EA 4) (REPD 2471, 800 MW, 32 km away) |
| GBA-0014706 | East Anglia THREE | under_construction | GBA-0002007 East Anglia 3 (EA 3) (REPD 2470, 1400 MW, 72 km away) |
| GBA-0014700 | East Anglia TWO | unknown | GBA-0002007 East Anglia 3 (EA 3) (REPD 2470, 1400 MW, 5 km away) |
| GBA-0014684 | Erebus Floating Wind Demo | consented | GBA-0005967 Erebus - Floating Offshore Wind Demonstration Project (REPD 7861, 100 MW, 49 km away) |
| GBA-0014685 | Five Estuaries | pre_planning | GBA-0006908 Five Estuaries - Wind Farm (REPD 9803, 1080 MW, 57 km away) |
| GBA-0014667 | Galloper | operational | GBA-0002054 Galloper Wind Farm (REPD 2526, 353 MW, 6 km away) |
| GBA-0014659 | Gunfleet Sands Demo | operational | GBA-0002019 Gunfleet Sands - (Demo) Extension (REPD 2488, 12 MW, 0 km away) |
| GBA-0014658 | Gunfleet Sands I | operational | GBA-0002020 Gunfleet Sands II (REPD 2489, 64.8 MW, 2 km away) |
| GBA-0014677 | Hornsea 1 (Centre) | operational |  |
| GBA-0014675 | Hornsea 1 (East) | operational | GBA-0002009 Hornsea 3 (REPD 2472, 2955 MW, 51 km away) |
| GBA-0014676 | Hornsea 1 (West) | operational | GBA-0002009 Hornsea 3 (REPD 2472, 2955 MW, 33 km away) |
| GBA-0014707 | Hornsea 4 | consented | GBA-0002010 Hornsea 4 (REPD 2473, 2400 MW, 46 km away) |
| GBA-0014694 | Hornsea Project 2 - Phase 1 (Breesea) | operational |  |
| GBA-0014681 | Hornsea Project 2 - Phase 2 (Soundmark) | operational |  |
| GBA-0014682 | Hornsea Project 2 - Phase 3 (Sonningmay) | operational |  |
| GBA-0014698 | Hornsea Project 3 (HOW03) | under_construction | GBA-0002009 Hornsea 3 (REPD 2472, 2955 MW, 76 km away) |
| GBA-0014665 | Humber Gateway | operational | GBA-0002066 Humber Gateway A (REPD 2544, 219 MW, 32 km away) |
| GBA-0014660 | Kentish Flats Extension | operational | GBA-0002023 Kentish Flats (REPD 2492, 90 MW, 3 km away) |
| GBA-0014662 | Lincs | operational |  |
| GBA-0014661 | London Array | operational | GBA-0002036 London Array Phase 2 (REPD 2507, 240 MW, 36 km away) |
| GBA-0014704 | Morecambe | consented |  |
| GBA-0014693 | Morlion (formerly Wave Hub) | consented |  |
| GBA-0014701 | Norfolk Boreas | consented |  |
| GBA-0014702 | Norfolk Vanguard East | unknown | GBA-0002015 The East Anglia Array - Norfolk Vanguard East (REPD 2484, 1380 MW, 38 km away) |
| GBA-0014703 | Norfolk Vanguard West | unknown | GBA-0014073 The East Anglia Array - Norfolk Vanguard West (REPD 20218, 1380 MW, 30 km away) |
| GBA-0014686 | North Falls | pre_planning | GBA-0007447 North Falls Offshore Wind Farm (REPD 10913, 1000 MW, no coordinates) |
| GBA-0014689 | R4 Project 1 (Dogger Bank South West) | unknown | GBA-0014072 Dogger Bank South West (REPD 20217, 1500 MW, no coordinates) |
| GBA-0014690 | R4 Project 2 (Dogger Bank South East) | unknown | GBA-0007576 Dogger Bank South East (REPD 11109, 1500 MW, no coordinates) |
| GBA-0014691 | R4 Project 3 (Outer Dowsing) | consented |  |
| GBA-0014692 | R4 Project 6 (Morgan) | consented |  |
| GBA-0014664 | Race Bank | operational | GBA-0002044 Race Bank (Phase 1) (REPD 2515, 289.8 MW, 23 km away) |
| GBA-0014668 | Rampion | operational | GBA-0005858 Rampion Wind Farm (Extension), (Rampion 2) (REPD 7698, 1200 MW, 8 km away) |
| GBA-0014687 | Rampion 2 (Rampion Extension) | planning | GBA-0005858 Rampion Wind Farm (Extension), (Rampion 2) (REPD 7698, 1200 MW, 22 km away) |

## 4. Potential duplicates awaiting review (not linked automatically)
Largest capacity first. Pairs with a high name score but no spatial/planning/identifier evidence are held for review, never merged.

| Asset | Name | Technology | MW | Best score | Candidates |
|---|---|---|---|---|---|
| GBA-0002009 | Hornsea 3 | wind_offshore | 2955 | 0.734 | 1 |
| GBA-0002010 | Hornsea 4 | wind_offshore | 2400 | 0.67 | 1 |
| GBA-0014072 | Dogger Bank South West | wind_offshore | 1500 | 0.8 | 1 |
| GBA-0007576 | Dogger Bank South East | wind_offshore | 1500 | 0.8 | 1 |
| GBA-0014830 | Dogger Bank South East CfD Unit A | wind_offshore | 1500 | 0.754 | 1 |
| GBA-0002007 | East Anglia 3 (EA 3) | wind_offshore | 1400 | 0.833 | 1 |
| GBA-0014073 | The East Anglia Array - Norfolk Vanguard West | wind_offshore | 1380 | 0.8 | 1 |
| GBA-0002032 | Hornsea 2 - Optimus and Breesea | wind_offshore | 1320 | 0.815 | 1 |
| GBA-0005858 | Rampion Wind Farm (Extension), (Rampion 2) | wind_offshore | 1200 | 0.833 | 1 |
| GBA-0004717 | East Anglia 2 (EA 2) | wind_offshore | 900 | 0.755 | 1 |
| GBA-0005859 | Awel y Mor Offshore Wind Farm | wind_offshore | 775 | 0.8 | 1 |
| GBA-0002052 | East Anglia 1 (EA 1) | wind_offshore | 714 | 0.833 | 1 |
| GBA-0002058 | Walney 3 | wind_offshore | 659 | 0.833 | 1 |
| GBA-0002040 | London Array Phase 1 | wind_offshore | 630 | 0.833 | 1 |
| GBA-0002065 | Gwynt y Mor | wind_offshore | 576 | 0.68 | 1 |
| GBA-0008038 | Green Volt - Offshore Wind Farm | wind_offshore | 560 | 0.88 | 1 |
| GBA-0006151 | Longfield | solar_pv | 500 | 0.86 | 1 |
| GBA-0007450 | West Burton Solar Project | solar_pv | 480 | 0.667 | 2 |
| GBA-0005252 | Viking Wind Farm | wind_onshore | 443 | 0.803 | 1 |
| GBA-0003789 | Viking Wind Farm | wind_onshore | 370 | 0.776 | 1 |
| GBA-0014825 | Hornsea Project Three Offshore Wind Farm AR6 C | wind_offshore | 360 | 0.846 | 1 |
| GBA-0014824 | Hornsea Project Three Offshore Wind Farm AR6 A | wind_offshore | 360 | 0.846 | 2 |
| GBA-0005144 | Sanquhar 2 Community Wind Farm | wind_onshore | 308 | 0.817 | 1 |
| GBA-0002042 | Centrica (Lincs) | wind_offshore | 270 | 0.712 | 1 |
| GBA-0002036 | London Array Phase 2 | wind_offshore | 240 | 0.778 | 1 |
| GBA-0005139 | Morlais Demonstration Zone | tidal_stream | 240 | 0.65 | 3 |
| GBA-0003766 | Stronelairg Wind Farm | wind_onshore | 227.7 | 0.601 | 1 |
| GBA-0014927 | West Burton Solar Project - AR7 - Site 2 | solar_pv | 182.6 | 0.856 | 1 |
| GBA-0014820 | Inch Cape A | wind_offshore | 177.41 | 0.615 | 1 |
| GBA-0005109 | Little Crow Solar Park | solar_pv | 150 | 0.86 | 1 |
| GBA-0005192 | Cloiche Wind Farm | wind_onshore | 125 | 0.814 | 1 |
| GBA-0002437 | Hadyard Hill | wind_onshore | 120 | 0.616 | 1 |
| GBA-0002021 | Gunfleet Sands Offshore Wind Scheme | wind_offshore | 108 | 0.833 | 1 |
| GBA-0004846 | Glendye Estate | wind_onshore | 104 | 0.769 | 1 |
| GBA-0002024 | Lynn | wind_offshore | 97.2 | 0.727 | 1 |
| GBA-0014926 | West Burton Solar Project - AR7 - Site 1 | solar_pv | 90.1 | 0.722 | 2 |
| GBA-0002023 | Kentish Flats | wind_offshore | 90 | 0.792 | 1 |
| GBA-0014833 | Norfolk Vanguard East CFD Unit B | wind_offshore | 90 | 0.782 | 1 |
| GBA-0003744 | Sandy Knowe Wind Farm | wind_onshore | 90 | 0.729 | 1 |
| GBA-0005177 | Sandy Knowe Wind Farm | wind_onshore | 81.6 | 0.759 | 1 |

## 5. Largest capacity discrepancies between quantities (installed vs contracted/registered)
These are different quantities and can legitimately differ; large gaps are listed first for investigation.

| Asset | Name | Installed MW | Other quantity | Other MW | Source |
|---|---|---|---|---|---|
| GBA-0005025 | Clash Gour | 225 | cfd_capacity_mw | 168.75 | cfd_results |
| GBA-0004820 | Limekiln Wind Farm | 79.8 | cfd_capacity_mw | 106 | cfd_results |
| GBA-0005708 | Bhlaraidh Wind Farm Extension | 84 | cfd_capacity_mw | 100.8 | cfd_results |
| GBA-0005040 | Blarghour Wind Farm | 84 | cfd_capacity_mw | 67.2 | cfd_results |
| GBA-0014161 | Berden Hall Solar Farm | 56 | cfd_capacity_mw | 40.25 | cfd_results |
| GBA-0006321 | Vianshill Farm, Parc Dyffryn - Solar Farm & Battery Storage | 65 | cfd_capacity_mw | 49.95 | cfd_results |
| GBA-0006354 | Elms Farm - Hinckley Solar Farm & Battery Storage | 49.9 | cfd_capacity_mw | 35 | cfd_results |
| GBA-0008762 | East End Solar Farm | 49.9 | cfd_capacity_mw | 35 | cfd_results |
| GBA-0008155 | Sunderlandwick Solar Farm | 49.9 | cfd_capacity_mw | 35 | cfd_results |
| GBA-0007476 | Callie's Solar Farm | 49.9 | cfd_capacity_mw | 36.56 | cfd_results |
| GBA-0008162 | Carlton Solar Farm | 49.99 | cfd_capacity_mw | 37.5 | cfd_results |
| GBA-0006017 | Perrinpit Farm | 49.9 | cfd_capacity_mw | 38.63 | cfd_results |
| GBA-0008653 | Straws Hadley Solar Farm | 49.9 | cfd_capacity_mw | 39.5 | cfd_results |
| GBA-0003798 | Loganhead Wind Farm | 25.6 | cfd_capacity_mw | 36 | cfd_results |
| GBA-0006348 | Horton Wood - Solar park | 49.9 | cfd_capacity_mw | 60 | cfd_results |
| GBA-0006608 | Forest Gate - Solar Farm & Battery Storage | 49.9 | cfd_capacity_mw | 40 | cfd_results |
| GBA-0006220 | Sheraton Hall Solar Farm | 49.9 | cfd_capacity_mw | 40 | cfd_results |
| GBA-0006362 | Leaps Rigg - Solar Farm | 49.9 | cfd_capacity_mw | 40 | cfd_results |
| GBA-0006365 | Burtree Lane - Solar farm | 49.9 | cfd_capacity_mw | 40 | cfd_results |
| GBA-0006613 | Leigh Delamere - Solar farm & Battery storage | 49.9 | cfd_capacity_mw | 40 | cfd_results |
| GBA-0007510 | Brogborough Landfill, Lidlington - Solar PV park | 40 | cfd_capacity_mw | 30.5 | cfd_results |
| GBA-0007697 | Tonmawr - Mynydd Fforch Dwm Wind Farm | 35 | cfd_capacity_mw | 26.8 | cfd_results |
| GBA-0011039 | Fibden Farm - Solar Array | 40 | cfd_capacity_mw | 32 | cfd_results |
| GBA-0007218 | Brick House Farm - Solar Farm | 49.9 | cfd_capacity_mw | 42 | cfd_results |
| GBA-0006866 | Burnt House Farm - Solar Farm | 49.99 | cfd_capacity_mw | 42.1 | cfd_results |
| GBA-0006864 | Low Horton Farm - Solar Farm | 49.99 | cfd_capacity_mw | 42.1 | cfd_results |
| GBA-0007474 | Montreathmont Moor Forest - Solar Farm & Battery Storage | 42 | cfd_capacity_mw | 34.37 | cfd_results |
| GBA-0004911 | Cressing Solar Farm (Phase 2) | 18 | cfd_capacity_mw | 24.9 | cfd_results |
| GBA-0006997 | Brynrhyd Solar Farm | 36 | cfd_capacity_mw | 30 | cfd_results |
| GBA-0006114 | Brynwell Farm | 21 | cfd_capacity_mw | 15.31 | cfd_results |
| GBA-0006954 | Lawns Solar Farm | 25 | cfd_capacity_mw | 20 | cfd_results |
| GBA-0009421 | South Lynch Farm - Solar Farm | 20 | cfd_capacity_mw | 15 | cfd_results |
| GBA-0006697 | Strathruddie, Kinglassie - Solar farm | 25 | cfd_capacity_mw | 20 | cfd_results |
| GBA-0008528 | Higher Hawkerland Farm, Sidmouth Road - Solar Farm | 18 | cfd_capacity_mw | 13.33 | cfd_results |
| GBA-0007587 | Old Hall Solar farm | 22.5 | cfd_capacity_mw | 17.91 | cfd_results |
| GBA-0008830 | Highfield Farm, Royston Road - Solar Farm & Battery Storage | 18 | cfd_capacity_mw | 13.5 | cfd_results |
| GBA-0003400 | Camilty Wind Farm | 25.8 | cfd_capacity_mw | 21.6 | cfd_results |
| GBA-0003399 | Abergorki Wind Farm | 13.5 | cfd_capacity_mw | 9.6 | cfd_results |
| GBA-0007181 | Wicken Farm, Leckhampstead - Solar Farm | 21 | cfd_capacity_mw | 17.25 | cfd_results |
| GBA-0006728 | Moat Farm - Solar Farm | 24.06 | cfd_capacity_mw | 20.34 | cfd_results |

## 6. Location coverage

59 of 14402 in-scope assets have no coordinates in any loaded source (flagged `missing_coordinates`).
