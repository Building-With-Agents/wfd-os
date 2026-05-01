# CFA Grant Agent — Project Context

## About This Project
This is the WJI Grant Financial Operations Agent for Computing for All (CFA), a 501(c)(3) nonprofit administering the WJI Good Jobs Challenge grant K8341 ($4,875,000, ESD Contract, runs through September 30, 2026). The agent automates monthly grant financial reconciliation, provider invoice validation, placement tracking, and ESD reporting.

**Primary users:** Krista (finance/QuickBooks) and Bethany (grant reporting/placements)
**Interface:** Microsoft Teams bot
**Built by:** Claude Code, Python

---

## Grant Overview

| Field | Value |
|---|---|
| Contract | K8341 |
| Funder | Washington State Employment Security Department (ESD) |
| ESD Contract Manager | Andrew Clemons (Andrew.Clemons@esd.wa.gov) |
| CFA Contract Manager | Ritu Bahl (ritu@computingforall.org) |
| Total Award | $4,875,000 |
| Period | January 1, 2024 – September 30, 2026 |
| PIP Minimum Threshold | 730 placements (triggering ESD Performance Improvement Plan review) |
| Full Target | 1,000 placements |

---

## Budget Structure — Amendment 1 Baseline (ONLY baseline — ignore original contract)

The Amendment 1 to Exhibit B was approved in November 2025 and is the sole governing budget document. The original contract budget is irrelevant for all reconciliation purposes.

### Budget Categories

| Category | Amended Budget |
|---|---|
| GJC Contractors (training/support providers) | $2,315,623.07 |
| CFA Contractors (AI Engage + Pete & Kelly Vargo) | $1,020,823.40 |
| Personnel: Salaries | $1,097,662.41 |
| Personnel: Benefits | $173,169.94 |
| Other Direct Costs (Travel, Comms, Supplies, Other) | $88,921.06 |
| Indirect Costs (de minimis 10%) | $178,798.91 |
| **TOTAL** | **$4,875,000.00** |

### CFA Contractors Detail
- AI Engage (Jason Mangold / AI Engage Group LLC): $245,000 amended budget
- CFA Contractors (Pete & Kelly Vargo): $775,823.40 amended budget

### Salaries & Benefits Detail (from Exhibit B Amendment 1)
- Travel: $6,309
- Communications: $1,773
- Supplies: $34,104
- Other: $46,736

---

## Training Providers — Payment Rates

### CRITICAL: $2,500 Flat Rate (applies from Q4 2025 onwards)
These providers were renegotiated in November 2025 to a flat $2,500 per verified WSAC placement:

| Provider | Amended Budget | Placement Target | Rate |
|---|---|---|---|
| Ada Developers Academy | $340,000 | 136 | $2,500/placement |
| Vets2Tech / St. Martin University | $260,000 | 105 | $2,500/placement |
| Apprenti | $42,500 | 17 | $2,500/placement |

### Legacy Rate Providers (original cost structure — includes wrap-around costs)
These providers kept their original per-placement rates:

| Provider | Amended Budget | Placement Target | Rate |
|---|---|---|---|
| Code Day X Mint | $251,342 | 78 | $3,222/placement (implied from budget ÷ target) |
| Per Scholas | $151,500 | 44 | $3,443/placement (implied from budget ÷ target) |
| Year Up Puget Sound | $212,500 | 81 | $2,623/placement (implied from budget ÷ target) |

### IMPORTANT: Invoice Validation Rule
When validating provider invoices for Q4 2025 and onwards:
- Expected invoice = verified WSAC placements × rate
- Flag if invoice differs from expected by more than $500
- Ada, Vets2Tech, Apprenti: always use $2,500 flat
- Code Day, Per Scholas, Year Up: use their legacy rates above

### ESD-Directed Contract Terminations (3 providers — NO further payments)
These contracts were terminated by ESD direction. Unspent balances stay in grant pool — ESD is NOT clawing back money paid.

| Provider | Amended Budget | QB Paid | Notes |
|---|---|---|---|
| WABS (Washington Alliance for Better Schools) | $238,050 | $184,416.81 | Last invoice ($53,633) not paid when contract ended. 0 placements. |
| NCESD 171 (North Central) | $484,452.43 | $459,452 | QB $25k below tracker — Q4 '25 invoice possibly unpaid. Net 56 placements after -19 Q1 '26 retraction. |
| Riipen / North Seattle College | $63,000 | $67,020 net | $82,303 refund confirmed in QB 1/12/26. Net $4k over amended budget. |

### Closed Providers with Placements (contracts complete)
| Provider | Amended Budget | QB Paid | Placements |
|---|---|---|---|
| PNW Cyber Challenge | $36,775.77 | $29,980 | 26 |

### Closed Support/Engagement Providers (not placement-based — 0 placements expected)
| Provider | QB Paid |
|---|---|
| Evergreen Goodwill | $80,339.25 |
| Seattle Jobs Initiative | $48,750 |
| WTIA | $27,625.23 |
| ESD 112 | $39,753 |
| I&CT (Bellevue College) | $18,197 |
| DynaTech Systems | $10,038 |

---

## Placement Data — Cumulative Through Q4 2025

Source: WSAC Partner_Data_Outcomes_Summary.xlsx (WSAC-reported verified placements)

| Provider | Q1 '24 | Q2 '24 | Q3 '24 | Q4 '24 | Q1 '25 | Q2 '25 | Q3 '25 | Q4 '25 | Total | Q1 '26 | Net |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Year Up | 16 | 15 | 6 | 5 | 18 | 14 | 7 | 5 | 86 | 0 | 86 |
| Ada | 29 | 1 | 28 | 1 | 19 | 0 | 2 | 2 | 82 | 0 | 82 |
| Vets2Tech | 0 | 11 | 8 | 11 | 14 | 15 | 4 | 5 | 68 | 0 | 68 |
| Code Day | 1 | 14 | 6 | 8 | 3 | 24 | 8 | 4 | 68 | 0 | 68 |
| NCESD | 0 | 2 | 5 | 5 | 8 | 10 | 45 | 0 | 75 | -19 | 56 |
| Per Scholas | 3 | 3 | 4 | 0 | 11 | 3 | 7 | 2 | 33 | 0 | 33 |
| PNW CCG | 0 | 0 | 2 | 0 | 13 | 5 | 1 | 5 | 26 | 0 | 26 |
| Riipen | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 4 | 0 | 4 |
| **TOTAL** | **49** | **46** | **60** | **31** | **87** | **72** | **74** | **23** | **442** | **-19** | **423** |

### Running Total Toward 730 PIP Threshold (as of March 28, 2026)
- Provider placements through Q4 2025: 442
- NCESD Q1 2026 retraction: -19
- AI Engage Q1 2026 placements: +93
- **Confirmed total: 516**
- Expected Q1 from active 6 providers (due April 6): ~30-40
- **Projected total: ~546-556**
- **Gap to 730 PIP threshold: ~174-184** (must come from WSAC verification queue via Gage)

### Q1 2026 Provider Projections (Bethany's estimates — due April 6)
| Provider | Expected | Status | Rate | Projected Payment |
|---|---|---|---|---|
| Vets2Tech | 24 | Guaranteed | $2,500 | $60,000 |
| Apprenti | 32 | Guaranteed | $2,500 | $80,000 |
| Ada | 13+ | 60+ outreach | $2,500 | $32,500+ |
| Code Day | 14 | Exceeds target | $3,222 | $45,108 |
| Per Scholas | 11 | Target goal | $3,443 | $37,873 |
| Year Up | 5 | Doc pending | $2,623 | $13,115 |
| **Total** | **99+** | Expected floor | | **~$268,596** |

---

## Key Financial Figures (as of March 28, 2026)

### QB Actuals (QB Vendor Report Jan 1 2024 – Mar 26 2026, pulled by Krista)
- GJC training/support provider payments: ~$1,737,913
- AI Engage: $140,000 (advance payments confirmed)
- CFA Contractors (Pete & Kelly Vargo): $670,606.81
- CFA Contractors subtotal: $810,606.81
- Salaries & overhead subtotal: $1,227,850.82 (Krista to break into sub-categories)

### Active Provider Balances
| Provider | Amended Budget | QB Paid | Remaining |
|---|---|---|---|
| Ada | $340,000 | $132,500 | $207,500 |
| Vets2Tech | $260,000 | $150,000 | $110,000 |
| Year Up | $212,500 | $165,000 | $47,500 |
| Code Day | $251,342 | $216,342 | $35,000 |
| Per Scholas | $151,500 | $108,500 | $43,000 |
| Apprenti | $42,500 | $0 | $42,500 |

---

## Reconciliation Rules

### Financial Reconciliation
1. Match QB transactions to bank statement line by line — flag unmatched items in either direction
2. Match QB transactions to credit card statement — flag charges over $1,000 not in QB
3. Categorize all expenses into six budget categories above
4. Calculate budget remaining per category
5. Calculate monthly burn rate and project remaining balance through September 30, 2026

### Invoice vs Placement Reconciliation
1. For each provider invoice received, look up their verified WSAC placements for same period
2. Calculate expected invoice: placements × rate (use $2,500 for Ada/Vets2Tech/Apprenti, legacy rates for others)
3. Flag if invoice differs from expected by more than $500
4. Flag any payment made with zero placements reported in that period
5. Track cumulative payments vs cumulative earned per provider (running balance model)

### The Running Balance Model
Providers were bootstrapped with upfront payments in early quarters. The reconciliation tracks:
- Cumulative paid to date
- Cumulative earned (placements × rate) to date
- Balance (positive = CFA overpaid, negative = CFA underpaid)

As of Q4 2025:
- Ada: CFA underpaid by ~$72,500 (Ada delivered more than paid for)
- Year Up: CFA underpaid by ~$30,000 (Year Up exceeded placement rate)
- Vets2Tech: roughly balanced (~$7,500 CFA underpaid)
- Code Day: roughly balanced (~$3,434 CFA underpaid)
- Per Scholas: roughly balanced
- NCESD: CFA significantly overpaid — core reason for contract termination

---

## Anomaly Detection Rules

Flag automatically without being asked:

1. Invoice amount doesn't match placement count × rate (tolerance: $500)
2. Payment made to provider with zero placements in that period
3. Budget category exceeding 90% of amended budget
4. Burn rate projecting overspend in any category before September 30, 2026
5. Provider placements declining quarter-over-quarter by more than 50%
6. Credit card charge over $1,000 not matched to QB
7. Any payment to WABS, NCESD, or Riipen (these contracts are terminated)
8. Apprenti invoice over $42,500 (budget cap — 17 placements × $2,500)
9. Code Day invoice that would cause cumulative payments to exceed $251,342
10. Ada invoice significantly above placement count (the Q4 $65k for 2 placements anomaly)

---

## Known Issues and Flags (as of March 28, 2026)

### Pending Clarification with Krista
1. **NCESD** — QB $25k below tracker. Is Q4 '25 invoice (inv# 1712600256, $25,136) still unpaid?
2. **Year Up** — QB $15k above tracker. Extra payment made after tracker's 2/23/26 cutoff?
3. **Per Scholas** — QB $7k below tracker. Recent invoice in transit?
4. **AI Engage** — $110k advance shown in tracker but not in QB under "AI Engage" — check under "AI Engage Group LLC" or "Jason Mangold"
5. **CFA Contractors** — Pete & Kelly Vargo — confirm QB vendor name

### Q4 2025 Invoice Discrepancies
- Ada invoiced $65,000 for Q4 but only 2 placements reported (expected $5,000 at $2,500 rate) — needs explanation
- Year Up invoiced $20,000 for Q4 — Bethany confirmed 8 placements (5 new + 3 previously reported) at $2,500 = $20,000 ✓
- Code Day invoiced $15,000 for Q4 — Bethany confirmed 6 placements (4 reported Q4 + 2 pushed to Q1) at $2,500 = $15,000 ✓

### NCESD Retraction
- NCESD reported -19 placements in Q1 2026 reducing their net from 75 to 56
- Cumulative cost per placement for NCESD at 56 net = $8,204/placement
- Contract terminated by ESD direction — no further payments

### Vets2Tech Q4 Miss
- Q4 2025: projected 36 placements, delivered only 5 — largest single-quarter miss
- Reason unknown — needs follow-up before April 18 PIP meeting

---

## Critical Dates

| Date | Event |
|---|---|
| March 31, 2026 | All GJC provider contracts close |
| April 6, 2026 | Q1 placement data due from all 6 active providers |
| April 6-17, 2026 | Gage cross-references placements in WSAC portal |
| April 18, 2026 | PIP meeting with ESD (Andrew Clemons) |
| April 20, 2026 | WSAC submission deadline |
| September 30, 2026 | Grant end date |

---

## Key Personnel

| Person | Role | Contact |
|---|---|---|
| Ritu Bahl | Executive Director, CFA | ritu@computingforall.org |
| Krista | Finance / QuickBooks | Internal |
| Bethany | Grant reporting / placement data | Internal |
| Gage | WSAC portal management | Internal |
| Andrew Clemons | ESD Contract Manager | Andrew.Clemons@esd.wa.gov |
| Jason Mangold | AI Engage (BD/strategy/placements) | External contractor |
| Pete & Kelly Vargo | CFA Contractors | External contractors |

---

## Data Sources

| Source | File | Last Updated | Authority |
|---|---|---|---|
| Budget baseline | K8341_GJC_CFA_WTWC_Exh_B_-RB_KJ_3_23_26__1_.xlsx | Nov 2025 (approved) | OFFICIAL — sole budget baseline |
| Invoice tracker | CFA_GJC_WJI_Grant_Invoice_Tracking_Master.xlsx | 2/23/26 | Internal tracker — may be stale |
| QB actuals | Computing_For_All_Expenses_by_Vendor_Summary.xlsx | 3/26/26 | AUTHORITATIVE — financial system of record |
| Payment history | GJC_Contractors_2024__1_.xlsx | Through Q4 2025 | Useful for quarterly payment breakdown |
| Placement data | Partner_Data_Outcomes_Summary.xlsx | WSAC-reported | AUTHORITATIVE for placement counts |

### Data Hierarchy (when sources conflict)
1. QB actuals win over tracker for payment amounts
2. WSAC portal data wins over provider-reported placements
3. Amendment 1 budget wins over original contract budget
4. Always use net placements (after retractions) for cost-per-placement calculations

---

## Allowable Expenses by Category

### Personnel: Salaries
- Wages for grant-funded staff with timesheets
- Named roles: Project Director, Project Manager, Finance Manager, Data Manager, WBL Portal Director, Education & Industry Engagement Manager
- Must not exceed Executive Level II (~$221k/year)

### Personnel: Benefits
- Employer FICA (7.65% of wages)
- FUTA/SUTA unemployment taxes
- Health/dental/vision (employer share only)
- Retirement contributions
- Workers compensation
- Paid leave (must match CFA's written HR policies)

### Other Direct Costs
- Travel: Site visits, ESD/WSAC meetings, EDA events — at Washington State rates
- Communications: Phone, internet, software subscriptions for grant work
- Supplies: Office supplies, equipment under $5,000/unit (over $5,000 needs ESD prior approval)
- Other: Employer engagement events, PEAR plan activities, marketing tied to grant programs

### Indirect Costs
- De minimis rate: 10% of modified total direct costs
- Cannot exceed 10% regardless of actual overhead
- Do NOT put AI Engage or CFA contractor payments here — those are subcontracts

### NOT Allowable
- AI Engage payments (goes in CFA Contractors line)
- Pete & Kelly Vargo payments (goes in CFA Contractors line)
- Training provider payments (goes in GJC Contractors line)
- Personal or non-grant business expenses

---

## Teams Bot Behavior

### Proactive Alerts
- Monthly: when new files detected in SharePoint WJI-Grant-Agent/monthly-uploads folder
- Immediate: when any anomaly is detected (flag with specific details)
- Weekly: burn rate update if any category exceeds 80% of budget

### Natural Language Queries — Examples

**Financial:**
- "What's our remaining balance by category?"
- "What's our monthly burn rate on salaries?"
- "Are we on track to stay within budget through September?"
- "What did we spend on [provider] last month?"
- "Show me all unmatched bank transactions this month"
- "Which credit card charges aren't in QB yet?"

**Placement:**
- "What's our cost per placement by provider?"
- "Which providers are behind on their placement targets?"
- "How many placements do we have toward the 730 PIP threshold?"
- "What's the projected final placement count?"

**Reconciliation:**
- "Which invoices don't match their placement counts?"
- "Show me all providers paid with zero placements"
- "What's the cumulative balance owed to Ada?"
- "Flag anything that looks wrong this month"

**Reporting:**
- "Draft the narrative section for ESD's Q1 quarterly report"
- "Generate the invoice to ESD for this month's reimbursement"
- "Which provider payment approvals are ready to send?"
- "Summarize this month's financial position in 3 bullets"

---

## Tech Stack

- **Language:** Python 3.11
- **AI Reasoning:** Claude API (claude-sonnet-4-20250514)
- **Bot Framework:** Microsoft Bot Framework SDK for Python
- **SharePoint/Teams:** Microsoft Graph API
- **Database:** PostgreSQL (monthly snapshots for trend analysis)
- **Local dev:** ngrok for Teams connectivity
- **Deployment:** Railway or Azure App Service
- **Azure App:** CFA-Grant-Agent (registered)
- **SharePoint site:** computingforall.sharepoint.com/sites/CFAOperationsHRFinance
- **SharePoint folder:** WJI-Grant-Agent/monthly-uploads

---

## Monthly Processing Workflow

### Week 1 — Krista drops files into SharePoint folder
1. QB Expenses by Vendor Summary CSV (pull from QuickBooks Online → Reports → Expenses by Vendor)
2. Bank of America bank statement CSV
3. Bank of America credit card statement CSV
4. Provider invoices as PDFs (one per provider)
5. WSAC placement data Excel (from Gage)

### Agent automatically runs
1. Read and parse all five file types
2. Match QB to bank statement — flag unmatched
3. Match QB to credit card — flag unmatched
4. Validate each provider invoice against WSAC placements
5. Update budget remaining by category
6. Calculate burn rate through September 2026
7. Update cumulative placement count toward 730
8. Post formatted summary to Teams channel

### Krista can then ask questions in Teams
Agent responds from stored PostgreSQL data — no re-processing needed

---

## Important Context for Code Review

When reviewing or explaining code to Ritu (non-developer), always:
1. Explain in plain English first — what does this do in terms of grant operations
2. Connect to specific business rules (e.g. "this is the part that checks whether Ada's invoice matches their WSAC placements at $2,500 per placement")
3. Flag if any business logic doesn't match the rules in this file
4. Avoid jargon — use grant terminology not programming terminology

Ritu's goal is technical independence — being able to understand what the agent is doing without relying on a developer for every explanation.

---

## Auto-Update Behavior

### When the Agent Should Update CLAUDE.md Automatically

The Teams bot agent must update this CLAUDE.md file automatically when any of the following events occur. Always show a diff to Krista or Ritu before saving, and require explicit approval ("yes update it" or "looks good") before writing.

### Trigger 1 — Monthly File Processing
When Krista drops the monthly files into SharePoint and the agent processes them, automatically update:
- QB actuals by category (replace "Pending QB" values with confirmed figures)
- Budget remaining per category
- Burn rate projection through September 2026
- Any new anomalies detected this month
- Add dated entry to Recent Updates log

### Trigger 2 — Q1 Placement Data (April 6, 2026)
When provider Q1 placement data arrives, automatically update:
- Q1 placement counts in the placement table for each provider
- Running total toward 730 PIP threshold
- Projected final placement count
- Q1 payment amounts owed per provider
- Add dated entry to Recent Updates log

### Trigger 3 — Provider Invoice Confirmed
When a provider invoice is validated and approved for payment, automatically update:
- QB paid amount for that provider
- Budget remaining for that provider
- Cumulative running balance (paid vs earned) for that provider
- Add dated entry to Recent Updates log

### Trigger 4 — Manual Instruction from Ritu or Krista
When Ritu or Krista says anything like:
- "Update the context file with..."
- "Remember that..."
- "Note that..."
- "Update CLAUDE.md..."
The agent should identify the correct section, propose the exact edit, show a diff, and wait for approval before saving.

### Trigger 5 — ESD/Andrew Meeting Notes
When Ritu shares notes from any ESD conversation, automatically:
- Extract key decisions and confirmed facts
- Add to the Known Issues section (resolving any flags that were clarified)
- Add dated entry to Recent Updates log

---

## Recent Updates Log

*This section is maintained automatically by the agent. Most recent entry first.*

**March 28, 2026 — Initial context file created**
- Full grant reconciliation completed through Q4 2025
- 423 net placements confirmed through Q4 2025
- AI Engage Q1 2026: 93 placements confirmed
- Running total toward 730: ~516 confirmed + ~30-40 expected April 6
- QB actuals confirmed: AI Engage $140k, CFA Contractors $670,606.81, Salaries/overhead subtotal $1,227,850.82
- Q4 2025 invoice discrepancies identified: Ada $65k for 2 placements (unexplained), Year Up and Code Day explained by Bethany
- CLAUDE.md created as permanent project context for Claude Code sessions

