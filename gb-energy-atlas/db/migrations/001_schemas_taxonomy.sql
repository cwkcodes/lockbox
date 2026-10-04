-- 001: schemas, helpers, controlled vocabularies (technology + status taxonomy)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE SCHEMA IF NOT EXISTS raw;    -- immutable copies of what each source published
CREATE SCHEMA IF NOT EXISTS norm;   -- source records mapped to one common shape (rebuildable from raw)
CREATE SCHEMA IF NOT EXISTS atlas;  -- canonical, resolved, published asset model
CREATE SCHEMA IF NOT EXISTS ops;    -- registry, audit, QA, review queues

CREATE OR REPLACE FUNCTION atlas.immutable_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT public.unaccent('public.unaccent', $1) $$;

-- ---------------------------------------------------------------------------
-- Technology taxonomy
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.technology (
  code         text PRIMARY KEY,
  label        text NOT NULL,
  family       text NOT NULL,
  category     text NOT NULL CHECK (category IN ('generation','storage','hybrid','other_low_carbon','unknown')),
  is_renewable boolean,            -- NULL = not applicable / not asserted (e.g. energy from waste)
  sort_order   int  NOT NULL DEFAULT 100,
  colour       text NOT NULL DEFAULT '#64748b',
  symbol       text NOT NULL DEFAULT 'circle',
  description  text
);

INSERT INTO atlas.technology (code,label,family,category,is_renewable,sort_order,colour,symbol,description) VALUES
 ('wind_onshore','Onshore wind','wind','generation',true,10,'#2f7fb5','circle',NULL),
 ('wind_offshore','Offshore wind (type unspecified)','wind','generation',true,11,'#0f4c81','ring','Foundation type not stated by the source'),
 ('wind_offshore_fixed','Offshore wind – fixed-bottom','wind','generation',true,12,'#0f4c81','ring',NULL),
 ('wind_offshore_floating','Offshore wind – floating','wind','generation',true,13,'#0b7285','ring',NULL),
 ('solar_pv','Solar PV','solar','generation',true,20,'#d98e04','square',NULL),
 ('bess','Battery energy storage (BESS)','storage','storage',NULL,30,'#7048b8','diamond','Electrochemical battery storage'),
 ('hydro','Hydroelectric','hydro','generation',true,40,'#1c8a8a','triangle','Run-of-river and storage hydro'),
 ('pumped_hydro','Pumped-storage hydro','hydro','storage',NULL,41,'#136f63','triangle-down',NULL),
 ('tidal_stream','Tidal stream','marine','generation',true,50,'#2b9348','hexagon',NULL),
 ('tidal_range','Tidal range / lagoon','marine','generation',true,51,'#2b9348','hexagon',NULL),
 ('wave','Wave energy','marine','generation',true,52,'#55a630','hexagon',NULL),
 ('anaerobic_digestion','Anaerobic digestion','bioenergy','generation',true,60,'#8a5a2b','pentagon',NULL),
 ('biomass','Biomass','bioenergy','generation',true,61,'#7a4a1d','pentagon','Dedicated and co-firing biomass'),
 ('landfill_gas','Landfill gas','bioenergy','generation',true,62,'#9c6b3a','pentagon',NULL),
 ('sewage_gas','Sewage gas','bioenergy','generation',true,63,'#a97c50','pentagon',NULL),
 ('geothermal','Geothermal electricity','geothermal','generation',true,70,'#c2410c','cross',NULL),
 ('renewable_chp','Renewable CHP','bioenergy','generation',true,71,'#92400e','pentagon',NULL),
 ('hybrid_wind_bess','Wind + BESS','hybrid','hybrid',NULL,80,'#4c6ef5','star','Only where a source explicitly records both technologies at one site'),
 ('hybrid_solar_bess','Solar + BESS','hybrid','hybrid',NULL,81,'#b5651d','star',NULL),
 ('hybrid_wind_solar','Wind + solar','hybrid','hybrid',true,82,'#3b82a0','star',NULL),
 ('hybrid_wind_solar_bess','Wind + solar + BESS','hybrid','hybrid',NULL,83,'#5b5bd6','star',NULL),
 ('hybrid_other','Other hybrid','hybrid','hybrid',NULL,84,'#6b7280','star',NULL),
 ('energy_from_waste','Energy from waste','other_low_carbon','other_low_carbon',NULL,90,'#6b7280','octagon','Not automatically classed as renewable'),
 ('advanced_conversion','Advanced conversion technologies','other_low_carbon','other_low_carbon',NULL,91,'#6b7280','octagon','Gasification / pyrolysis etc.'),
 ('hydrogen','Hydrogen (electrolysers / fuel cells)','other_low_carbon','other_low_carbon',NULL,92,'#0ea5a4','octagon',NULL),
 ('ldes','Long-duration energy storage','other_low_carbon','other_low_carbon',NULL,93,'#8b5cf6','octagon','Liquid air, thermal, gravity and similar'),
 ('caes','Compressed-air energy storage','other_low_carbon','other_low_carbon',NULL,94,'#8b5cf6','octagon',NULL),
 ('flow_battery','Flow battery','other_low_carbon','other_low_carbon',NULL,95,'#8b5cf6','octagon',NULL),
 ('other_storage','Other storage (flywheel etc.)','other_low_carbon','other_low_carbon',NULL,96,'#8b5cf6','octagon',NULL),
 ('other_low_carbon','Other low-carbon infrastructure','other_low_carbon','other_low_carbon',NULL,99,'#6b7280','octagon',NULL),
 ('unknown','Unknown technology','unknown','unknown',NULL,200,'#94a3b8','circle',NULL);

-- ---------------------------------------------------------------------------
-- Status taxonomy (source wording is always preserved separately)
-- ---------------------------------------------------------------------------
CREATE TABLE atlas.status (
  code        text PRIMARY KEY,
  label       text NOT NULL,
  stage_group text NOT NULL CHECK (stage_group IN ('operational','pipeline','historic','unsuccessful','unknown')),
  sort_order  int  NOT NULL,
  pattern     text NOT NULL DEFAULT 'outline'  -- visual encoding: solid | half | outline | muted | cross
);
INSERT INTO atlas.status (code,label,stage_group,sort_order,pattern) VALUES
 ('operational','Operational','operational',10,'solid'),
 ('partially_operational','Partially operational','operational',11,'solid'),
 ('commissioning','Commissioning','pipeline',20,'half'),
 ('under_construction','Under construction','pipeline',21,'half'),
 ('repowering_under_construction','Repowering under construction','pipeline',22,'half'),
 ('awaiting_construction','Awaiting construction','pipeline',30,'outline'),
 ('connection_agreed','Grid connection agreed (not yet connected)','pipeline',33,'outline'),
 ('consented','Consented','pipeline',31,'outline'),
 ('repowering_consented','Repowering consented','pipeline',32,'outline'),
 ('planning_submitted','Planning submitted','pipeline',40,'outline'),
 ('planning','Planning','pipeline',41,'outline'),
 ('repowering_proposed','Repowering proposed','pipeline',42,'outline'),
 ('cfd_awarded','CfD awarded (development stage not stated)','pipeline',45,'outline'),
 ('scoping','Scoping','pipeline',50,'outline'),
 ('pre_planning','Pre-planning','pipeline',51,'outline'),
 ('mothballed','Mothballed','historic',60,'muted'),
 ('decommissioned','Decommissioned','historic',61,'muted'),
 ('withdrawn','Withdrawn','unsuccessful',70,'cross'),
 ('refused','Refused','unsuccessful',71,'cross'),
 ('expired','Expired','unsuccessful',72,'cross'),
 ('cancelled','Cancelled / abandoned','unsuccessful',73,'cross'),
 ('superseded','Superseded by re-application','unsuccessful',74,'cross'),
 ('unknown','Unknown','unknown',99,'muted');
