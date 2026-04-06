# Phase 1g: College Program Intelligence Discovery
**Date:** 2026-04-02

---

## College/Program Data Sources

### Dataverse (Primary)

| Entity | Records | Content |
|--------|---------|---------|
| cfa_collegeprograms | 729 | College/university program profiles |
| cfa_careerprograms | 3,940 | Career Bridge program listings (WA state) |

### SQL/BACPAC (Supplementary)

| Table | Est. Size | Content |
|-------|----------|---------|
| edu_providers | 59 KB | Educational institutions |
| programs | 76 KB | Academic programs |
| provider_programs | 318 KB | M2M: institution ↔ program |
| cip | 2.0 MB | CIP taxonomy (Classification of Instructional Programs) |
| socc / socc_2010 / socc_2018 | ~277 KB | SOC occupation codes (3 versions) |
| cip_to_socc_map | 280 KB | CIP ↔ SOC crosswalk |

## Skills Taxonomy Mapping

The CIP-to-SOC crosswalk is fully built in the SQL database, enabling:
- "Which programs train students for which occupations?"
- "What SOC codes align with this CIP program code?"

However, there is **no direct program-to-skills mapping** found.
The skills taxonomy (5,061 skills) is not linked to college programs
or career programs in any discovered data source.

## Pipeline Match Feature

No evidence of automated talent pipeline matching between:
- Employer requests → college programs producing matching graduates
- College program outputs → market demand signals

This is a key capability for the College Pipeline Agent to build.

## College Engagement Level

| Signal | Evidence |
|--------|----------|
| College programs entered | 729 programs in Dataverse |
| Career programs (WA state) | 3,940 programs |
| Institutions profiled | Unknown (need edu_providers count) |
| Active partnerships | No tracking found |
| Graduate outcome tracking | No data found |

---

## Summary for College Pipeline Agent Build

| Asset | Status | Action |
|-------|--------|--------|
| 729 college programs | Ready to migrate | Migrate from Dataverse |
| 3,940 career programs | Ready to migrate | Migrate from Dataverse |
| CIP taxonomy | In BACPAC | Migrate to PostgreSQL |
| SOC codes (3 versions) | In BACPAC | Migrate to PostgreSQL |
| CIP-to-SOC crosswalk | In BACPAC | Migrate to PostgreSQL |
| edu_providers + programs | In BACPAC | Migrate to PostgreSQL |
| Program-to-skills mapping | Does not exist | Build using CIP→SOC→skills chain |
| Employer-program matching | Does not exist | Build as College Pipeline Agent |
| Graduate tracking | Does not exist | Build as Stage 7 integration |
