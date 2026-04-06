# Market Intelligence Agent — Detailed Technical Specification
**WFD OS / Waifinder | Computing for All**
**Date:** 2026-03-28
**Status:** Ready to build — all data sources confirmed live

---

## 1. Purpose

The Market Intelligence Agent answers labor market questions in plain language. It is the intelligence layer that tells workforce boards, employers, colleges, and students what skills are in demand, which employers are hiring, what jobs pay, and how programs align to market need.

**First deployment:** Workforce Solutions Borderplex (El Paso, TX) — active client.
**This agent IS the Job Intelligence Engine (JIE)** being built for the Texas border region.

---

## 2. What It Does — User-Facing Capabilities

The agent answers questions like:

| Question | Data Source |
|----------|-------------|
| "What are the top skills employers are asking for right now?" | `cfa_toplightcastskills` |
| "Which companies are posting the most tech jobs in Washington?" | `cfa_topcompaniespostings` |
| "What does a network administrator earn in WA state?" | `cfa_advertisedwagetrends` |
| "Show me all QA Tester job postings and the skills they require" | `cfa_lightcastjobs` |
| "Which skills are growing fastest vs. lagging in the market?" | `cfa_toplightcastskills` (growth fields) |
| "What jobs match a student with Python and SQL skills?" | `cfa_lightcastjobs` (skills field) |
| "How many postings are there for cloud roles vs. cybersecurity?" | `cfa_lightcastjobs` + `cfa_toplightcastskills` |
| "Which programs at WA colleges align with what employers need?" | `cfa_careerbridgedatas` + `cfa_toplightcastskills` |

---

## 3. Data Sources

### 3.1 Confirmed Live Data (Dataverse — working today)

#### `cfa_lightcastjobs` — 2,670 Job Postings
Full job postings from Lightcast (external labor market data provider).

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cfa_lightcastjobid` | GUID | Primary key | `54f928f9-34a1-ef11...` |
| `cfa_name` | string | Job title | `"Quality Assurance Testers"` |
| `cfa_company` | string | Employer name | `"Solutions Through Innovative Technologies"` |
| `cfa_location` | string | Location | `"Olympia, WA"` |
| `cfa_description` | string | Full job description | Full text, 1,000–3,000 words |
| `cfa_skills` | string | Comma-separated skill list | `"Python, SQL, Agile, JIRA..."` |
| `cfa_onetcode` | string | O*NET occupation code | `"15-1253.00"` |
| `cfa_url` | string | Original posting URL | `"https://..."` |
| `cfa_datestring` | string | Posting date label | `"Nov 2024 - Active"` |
| `cfa_internalnumber` | string | Internal reference | `"LC-2637"` |
| `createdon` | datetime | Date added to Dataverse | `2024-11-12T20:31:12Z` |

**Notes:**
- Skills field is comma-separated — needs parsing on ingest
- O*NET codes enable cross-referencing with occupation classifications
- Data is from Lightcast Q3 2024 dataset (WA state focus)

---

#### `cfa_toplightcastskills` — 150 Top Skills
Aggregated skill demand data — what skills appear most in job postings.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cfa_toplightcastskillid` | GUID | Primary key | |
| `cfa_skill` | string | Skill name | `"Active Directory"` |
| `cfa_postings` | int | Number of postings requiring skill | `171` |
| `cfa_percentoftotalpostings` | float | % of all postings needing skill | `45` |
| `cfa_profiles` | int | Number of candidate profiles with skill | `3,528` |
| `cfa_percentoftotalprofiles` | float | % of profiles listing skill | `11` |
| `cfa_skillgrowthrelativetomarket` | string | Growth trend | `"Rapidly Growing"` / `"Lagging"` |
| `cfa_projectedskillgrowth` | float | Projected % growth | `22.6` |
| `cfa_skilltype` | int (enum) | Skill category | `705000002` |
| `cfa_paramregion` | string | Region filter used | `"Washington"` |
| `cfa_paramtimeframe` | string | Time period | `"Aug 2023 - Jul 2024"` |
| `cfa_paramminexprequired` | string | Experience level filter | `"0 years - 3 years"` |
| `cfa_parameducationlevel` | string | Education filter | `"Any"` |
| `cfa_paramjobtype` | string | Job type filter | `"Include Internships"` |
| `cfa_tabnameinsourceexcelsheet` | string | Skill category label | `"Top Software Skills"` |

**Notes:**
- `cfa_skillgrowthrelativetomarket` is the key field for trend analysis
- Supply/demand gap = high `cfa_percentoftotalpostings` vs. low `cfa_percentoftotalprofiles`
- `cfa_tabnameinsourceexcelsheet` groups skills: "Top Software Skills", "Top Specialized Skills", etc.

---

#### `cfa_advertisedwagetrends` — 12 Wage Records
Monthly advertised wage data by occupation and region.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cfa_advertisedwagetrendid` | GUID | Primary key | |
| `cfa_advertisedwage` | string | Median advertised hourly wage | `"43.2"` |
| `cfa_monthyear` | string | Month of data | `"Jul 2024"` |
| `cfa_jobpostings` | int | Number of postings that month | `21` |
| `cfa_paramregion` | string | Region | `"Washington"` |
| `cfa_paramtimeframe` | string | Time range | `"Aug 2023 - Jul 2024"` |
| `cfa_parameducationlevel` | string | Education filter | `"Any"` |
| `cfa_paramminexprequired` | string | Experience filter | `"0 years - 3 years"` |

**Notes:**
- 12 records = monthly time series for one occupation/region combination
- Additional occupation/region combinations can be added as new Lightcast reports are imported
- `cfa_advertisedwage` should be cast to float for calculations

---

#### `cfa_topcompaniespostings` — 50 Company Records
Which companies post the most jobs.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cfa_topcompaniespostingid` | GUID | Primary key | |
| `cfa_company` | string | Company name | `"State of Washington"` |
| `cfa_totalaug2023july2024` | int | Total postings in period | `438` |
| `cfa_uniqueaug2023july2024` | int | Unique postings (deduped) | `68` |
| `cfa_medianpostingduration` | string | Avg days posting stays live | `"38 days"` |
| `cfa_paramregion` | string | Region | `"Washington"` |
| `cfa_paramtimeframe` | string | Time period | `"Aug 2023 - Jul 2024"` |

---

#### `cfa_toppostedjobtitles` — 50 Job Title Records
Most frequently posted job titles.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cfa_toppostedjobtitleid` | GUID | Primary key | |
| `cfa_uniqueaug2023july2024` | int | Unique postings for this title | — |
| `cfa_paramregion` | string | Region | `"Washington"` |

---

#### `cfa_jobpostingsregionalbreakdowns` — 5 Regional Records
Job posting counts broken down by MSA (Metropolitan Statistical Area).

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cfa_msa` | string | Metro area name | — |
| `cfa_aug2023july2024` | int | Posting count for period | — |
| `cfa_paramregion` | string | State/region | — |

---

#### `cfa_careerbridgedatas` — 5,834 Program Completion Records
Washington state Career Bridge data — completions by program, institution, and region.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cfa_careerbridgedataid` | GUID | Primary key | |
| `cfa_completers` | int | Program completers count | — |
| `cfa_mainfips` | string | Geographic FIPS code | — |
| `cfa_loczip3` | string | ZIP prefix (3-digit) | — |
| `cfa_loctitle2–8` | string | Location hierarchy labels | — |
| `cfa_percentgenderfemale` | float | % female completers | — |
| `cfa_percentunder20` | float | % under age 20 | — |
| `cfa_percentage3039` | float | % age 30–39 | — |
| `cfa_empindj` | string | Employment industry code | — |
| `cfa_percentindf/d/i` | float | Diversity breakdowns | — |

**Notes:**
- Links to `cfa_collegeprograms` and CIP/SOC mapping for program-to-market alignment
- Primary data source for the College Pipeline Agent overlap

---

### 3.2 Phase 2 Data (PostgreSQL — requires password reset first)

| Table | Records | Description |
|-------|---------|-------------|
| `skills` | 5,034 | Full skill taxonomy with 1,536-dim embeddings (260 MB) |
| `job_postings` | ~500 | Internal job postings with structured fields |
| `skill_subcategories` | — | Taxonomy hierarchy |
| `cip_to_socc_map` | — | Education-to-occupation bridge |
| `socc` | — | Standard Occupational Classification codes |
| `postal_geo_data` | — | Geographic reference data |

---

## 4. Agent Tools

The agent exposes these tools to Claude. Each tool is a Python function that queries Dataverse or PostgreSQL and returns structured results.

---

### Tool 1: `get_top_skills`
Returns the most in-demand skills, optionally filtered by region, experience level, or skill type.

```python
def get_top_skills(
    region: str = "Washington",
    experience_level: str = "0 years - 3 years",
    limit: int = 20,
    skill_category: str = None,   # e.g. "Top Software Skills"
    growth_filter: str = None,    # e.g. "Rapidly Growing"
) -> list[dict]:
    """
    Returns skills ranked by posting count with supply/demand gap analysis.

    Returns:
        List of {skill, postings, percent_of_postings, profiles,
                 percent_of_profiles, supply_demand_gap, growth_trend,
                 projected_growth}
    """
```

**Supply/demand gap calculation:**
`gap = cfa_percentoftotalpostings - cfa_percentoftotalprofiles`
Positive = employer demand exceeds worker supply (skills shortage)

---

### Tool 2: `search_jobs`
Searches job postings by title, skill, company, or O*NET code.

```python
def search_jobs(
    query: str = None,           # Free text search on title + description
    skills: list[str] = None,    # Filter by required skills
    company: str = None,         # Filter by employer
    location: str = None,        # Filter by location
    onet_code: str = None,       # Filter by O*NET occupation code
    limit: int = 20,
) -> list[dict]:
    """
    Returns matching job postings with title, company, location, skills, URL.
    """
```

**Implementation note:** Dataverse OData supports `$filter` and `$search`. Skill matching on `cfa_skills` uses `contains()`.

---

### Tool 3: `get_wage_trends`
Returns advertised wage data and trend over time.

```python
def get_wage_trends(
    region: str = "Washington",
    experience_level: str = "0 years - 3 years",
) -> dict:
    """
    Returns monthly wage trend series and summary statistics.

    Returns:
        {median_wage, min_wage, max_wage, trend_direction,
         monthly_series: [{month, wage, postings}]}
    """
```

---

### Tool 4: `get_top_employers`
Returns companies posting the most jobs with hiring velocity metrics.

```python
def get_top_employers(
    region: str = "Washington",
    limit: int = 20,
) -> list[dict]:
    """
    Returns employers ranked by posting volume.

    Returns:
        List of {company, total_postings, unique_postings,
                 median_posting_duration_days}
    """
```

---

### Tool 5: `get_market_summary`
High-level market snapshot — designed for the Borderplex demo opening.

```python
def get_market_summary(
    region: str = "Washington",
) -> dict:
    """
    Returns a structured market overview combining all data sources.

    Returns:
        {total_job_postings, top_5_skills, top_5_employers,
         top_5_job_titles, median_wage, fastest_growing_skill,
         biggest_supply_demand_gap, data_as_of}
    """
```

---

### Tool 6: `compare_skills_to_market`
Takes a list of skills (e.g. a student's skill set) and compares against market demand.

```python
def compare_skills_to_market(
    skills: list[str],
    region: str = "Washington",
) -> dict:
    """
    Compares input skills against market demand data.

    Returns:
        {matched_skills: [{skill, demand_rank, postings, growth}],
         missing_high_demand_skills: [{skill, postings, gap}],
         market_alignment_score: float,  # 0-1
         recommendation: str}
    """
```

---

### Tool 7: `get_program_market_alignment` *(Phase 2 — needs College Pipeline Agent)*
Scores a college program against current market demand.

```python
def get_program_market_alignment(
    program_name: str = None,
    cip_code: str = None,
) -> dict:
    """
    Maps program completers to occupation demand via CIP → SOC → job postings.
    Requires: cfa_careerbridgedatas + cip_to_socc_map + cfa_lightcastjobs
    """
```

---

## 5. System Prompt

```
You are the Market Intelligence Agent for Waifinder, a workforce development platform
built by Computing for All.

Your job is to answer labor market questions using real job posting data, skill demand
data, wage trends, and employer hiring patterns. All data comes from Lightcast
(a leading labor market analytics provider) and is current as of Q3 2024.

You have access to the following tools:
- get_top_skills: What skills are employers asking for?
- search_jobs: Find specific job postings
- get_wage_trends: What do these roles pay?
- get_top_employers: Which companies are hiring?
- get_market_summary: Give me a market overview
- compare_skills_to_market: How do these skills match market demand?

Always cite data when giving answers (e.g., "Based on 2,670 Lightcast job postings...").
Be specific and quantitative. Workforce boards and employers expect data, not generalities.

When data is from Q3 2024 and may be dated, say so clearly.
When a question requires data you don't have (e.g., real-time postings), say so and
explain what you can answer.

Current deployment context: Workforce Solutions Borderplex — serving the El Paso,
TX / Ciudad Juárez border region. Tailor answers to workforce development use cases:
employer partnerships, training program alignment, student career guidance.
```

---

## 6. File Structure

```
wfd-os/
└── agents/
    └── market-intelligence/
        ├── agent.py              ← Main agent (Claude + tools)
        ├── tools/
        │   ├── __init__.py
        │   ├── skills.py         ← get_top_skills, compare_skills_to_market
        │   ├── jobs.py           ← search_jobs
        │   ├── wages.py          ← get_wage_trends
        │   ├── employers.py      ← get_top_employers
        │   └── summary.py        ← get_market_summary
        ├── dataverse/
        │   ├── __init__.py
        │   └── client.py         ← Dataverse API wrapper (auth + requests)
        ├── tests/
        │   ├── test_tools.py     ← Unit tests for each tool
        │   └── test_agent.py     ← Integration tests
        ├── demo.py               ← Borderplex demo script
        └── requirements.txt
```

---

## 7. Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Agent framework | Anthropic Claude API | `claude-opus-4` for reasoning |
| Data source (Phase 1) | Microsoft Dataverse Web API | Auth via client credentials — working |
| Data source (Phase 2) | PostgreSQL `talent_finder` | Needs password reset |
| HTTP client | `httpx` or `requests` | Dataverse API calls |
| Auth | `msal` or direct OAuth2 | Client credentials flow |
| Testing | `pytest` | |
| Environment | Python 3.11 | |

---

## 8. Authentication

Dataverse auth is already working. Use the pattern confirmed live:

```python
import requests
import os

def get_dataverse_token():
    resp = requests.post(
        f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.getenv("AZURE_CLIENT_ID"),
            "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
            "scope": f"{os.getenv('DYNAMICS_PRIMARY_URL')}/.default",
        }
    )
    return resp.json()["access_token"]
```

Required `.env` variables (already in `wfd-os/.env`):
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `DYNAMICS_PRIMARY_URL` = `https://cfahelpdesksandbox.crm.dynamics.com`
- `ANTHROPIC_API_KEY` ← needs to be added

---

## 9. Build Plan

### Week 1 — Data Layer + Tools
- [ ] Set up `agents/market-intelligence/` folder structure
- [ ] Build `dataverse/client.py` — authenticated Dataverse wrapper
- [ ] Build `tools/skills.py` — `get_top_skills` + `compare_skills_to_market`
- [ ] Build `tools/jobs.py` — `search_jobs`
- [ ] Build `tools/wages.py` — `get_wage_trends`
- [ ] Build `tools/employers.py` — `get_top_employers`
- [ ] Build `tools/summary.py` — `get_market_summary`
- [ ] Write unit tests for each tool
- [ ] Verify all tools return correct data against live Dataverse

### Week 2 — Agent + Demo
- [ ] Build `agent.py` — Claude agent with all tools wired up
- [ ] Write system prompt and test with sample Borderplex questions
- [ ] Build `demo.py` — scripted Borderplex demo scenario
- [ ] Integration tests — agent answers 10 sample questions correctly
- [ ] Reset PostgreSQL password and load skill embeddings (Phase 2 prep)

### Week 3 — Borderplex Demo
- [ ] Run live demo with Borderplex stakeholders
- [ ] Collect feedback → iterate

---

## 10. Sample Borderplex Demo Script

These are the questions the agent should answer live at the Borderplex demo:

1. **"Give me a market overview for the Washington tech sector"**
   → `get_market_summary()` — total postings, top skills, top employers, median wage

2. **"What are the top 10 skills employers are asking for that entry-level candidates are least likely to have?"**
   → `get_top_skills(limit=10)` — sorted by supply/demand gap descending

3. **"Which skills are growing fastest in the market?"**
   → `get_top_skills(growth_filter="Rapidly Growing")`

4. **"What does a network administrator earn, and is demand growing?"**
   → `get_wage_trends()` + `get_top_skills(query="network")`

5. **"Which companies are hiring the most entry-level tech talent?"**
   → `get_top_employers()`

6. **"A student knows Python, SQL, and Excel. How well do their skills match the market?"**
   → `compare_skills_to_market(skills=["Python", "SQL", "Excel"])`

7. **"Show me all QA tester job postings and what skills they require"**
   → `search_jobs(query="QA tester")`

---

## 11. Success Criteria

| Metric | Target |
|--------|--------|
| All 7 tools return correct data | 100% |
| Agent answers all 7 demo questions accurately | 100% |
| Response time per question | < 10 seconds |
| Demo runs without errors | Pass |
| Dataverse connection stable | 100% uptime during demo |
