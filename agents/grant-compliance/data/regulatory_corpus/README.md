# Regulatory corpus — Compliance Requirements Agent

This directory holds the regulatory source-of-truth text the Compliance
Requirements Agent reads when generating Mode A documentation requirement
sets and answering Mode B Q&A. See
`agents/grant-compliance/docs/compliance_requirements_agent_spec.md` for
the agent that consumes it.

**The agent's output quality depends on this corpus's accuracy.** Every
requirement the agent emits must cite a specific section in this corpus.
Outputs that don't cite an in-corpus section are rejected at validation.
That makes corpus integrity a hard constraint, not a soft one.

## Scope

In scope for v1 (per spec §"Scope: what the agent covers"):

- 2 CFR 200 Subpart D — Procurement Standards (§§200.317–200.327)
- 2 CFR 200 Subpart D — Subrecipient Monitoring (§§200.331–200.333)
- 2 CFR 200 Subpart D — Standards of Conduct / Conflicts of Interest (§200.318(c), already covered inside §200.318)
- 2 CFR 200 Subpart E — Cost Principles, §200.404 Reasonable costs
- 2025 OMB Compliance Supplement, Part 4-11.300 (Economic Development Cluster, Assistance Listing 11.307)

Out of scope (handled elsewhere or deferred):

- Subpart F (Audit Requirements) — covered by Audit Readiness work
- Subpart B (General Provisions) — covered indirectly through other subparts
- §200.430 Time and effort certifications — covered by the v1.3.3 dimension
- §200.414 Indirect cost rate methodology — covered by Allowable Costs dimension
- Other federal grant programs beyond Economic Development Cluster

## Layout

```
README.md             — this file
manifest.json         — machine-readable index for corpus.py
cfr_2_part_200/
  subpart_d_procurement/
    200.317.txt       Procurements by states
    200.318.txt       General procurement standards (incl. (c) conflict of interest)
    200.319.txt       Competition
    200.320.txt       Methods of procurement to be followed
    200.321.txt       Contracting w/ small / minority / women's / labor-surplus / veteran-owned firms
    200.322.txt       Domestic preferences for procurements
    200.323.txt       Procurement of recovered materials
    200.324.txt       Contract cost and price
    200.325.txt       Federal awarding agency or pass-through entity review
    200.326.txt       Bonding requirements
    200.327.txt       Contract provisions
  subpart_d_subrecipient/
    200.331.txt       Subrecipient and contractor determinations
    200.332.txt       Requirements for pass-through entities
    200.333.txt       Fixed amount subawards
  subpart_e_cost_principles/
    200.404.txt       Reasonable costs
omb_compliance_supplement_2025/
  part_4_11.300_economic_development_cluster.txt
```

## File format

Every corpus file starts with a header block. The header is parsed by
`corpus.py` and used to construct citations and verification metadata
when the agent emits requirements.

```
========================================================================
CITATION:        <e.g., 2 CFR 200.318>
TITLE:           <section title>
SUBPART:         <D | E>
PART:            200 — Uniform Administrative Requirements, Cost Principles, and Audit Requirements for Federal Awards
SOURCE_URL:      <eCFR or govinfo URL>
EFFECTIVE_DATE:  <YYYY-MM-DD>  (per the 2024 final rule unless noted)
VERIFICATION:    <verbatim | structured-paraphrase | skeleton>
LAST_UPDATED:    <YYYY-MM-DD>
NOTES:           <free-form notes — e.g. "see 89 FR 30046 for amendment history">
========================================================================

(regulation body)
```

## Verification status — what the labels mean

The `VERIFICATION` field is the most important honesty marker in the corpus.
It tells both the agent and a human reviewer how to treat the file's body.

- **`verbatim`** — text reproduced from the regulation as it appears in
  the official source (eCFR for CFR sections, govinfo.gov for the
  Compliance Supplement). The agent may quote this text directly when
  citing the section.

- **`mixed-verbatim-paraphrase`** — some paragraphs of the file are
  verbatim and clearly delimited inline by `[VERBATIM_START — <provenance>]`
  and `[VERBATIM_END]` markers; the rest is structured-paraphrase. The
  agent's prompts read these markers and apply the verbatim-vs-paraphrase
  rule per paragraph rather than per file. Used when only a specific
  subsection has been upgraded to verbatim — e.g., §200.318(c) was
  upgraded ahead of the rest of §200.318 because the conflict-of-interest
  paragraph is heavily referenced in the Phouang counsel review.

- **`structured-paraphrase`** — text reflects the regulation's substance
  and structure but may not match the exact wording of the official source.
  The agent should describe requirements based on this content but should
  NOT quote it as if it were the regulation's exact words. Human reviewers
  should verify any agent-emitted quotation against the official source
  before treating it as authoritative.

- **`skeleton`** — placeholder file documenting what content the file
  should hold once populated from the official source. Body is intentionally
  empty or describes the missing content. The agent should refuse to cite
  skeleton files; a human must populate them before the agent's output is
  trustworthy in that area.

The current state of every file is recorded in `manifest.json` and shown
in the table below.

## Provenance

| File | Verification | Source URL |
|---|---|---|
| `cfr_2_part_200/subpart_d_procurement/200.317.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.317 |
| `cfr_2_part_200/subpart_d_procurement/200.318.txt` | mixed-verbatim-paraphrase (¶ (c) verbatim) | https://www.ecfr.gov/current/title-2/section-200.318 |
| `cfr_2_part_200/subpart_d_procurement/200.319.txt` | **verbatim** | https://www.ecfr.gov/current/title-2/section-200.319 |
| `cfr_2_part_200/subpart_d_procurement/200.320.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.320 |
| `cfr_2_part_200/subpart_d_procurement/200.321.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.321 |
| `cfr_2_part_200/subpart_d_procurement/200.322.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.322 |
| `cfr_2_part_200/subpart_d_procurement/200.323.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.323 |
| `cfr_2_part_200/subpart_d_procurement/200.324.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.324 |
| `cfr_2_part_200/subpart_d_procurement/200.325.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.325 |
| `cfr_2_part_200/subpart_d_procurement/200.326.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.326 |
| `cfr_2_part_200/subpart_d_procurement/200.327.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.327 |
| `cfr_2_part_200/subpart_d_subrecipient/200.331.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.331 |
| `cfr_2_part_200/subpart_d_subrecipient/200.332.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.332 |
| `cfr_2_part_200/subpart_d_subrecipient/200.333.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.333 |
| `cfr_2_part_200/subpart_e_cost_principles/200.404.txt` | structured-paraphrase | https://www.ecfr.gov/current/title-2/section-200.404 |
| `omb_compliance_supplement_2025/part_4_11.300_economic_development_cluster.txt` | skeleton | https://www.whitehouse.gov/omb/management/office-federal-financial-management/ |

## Why "structured-paraphrase" for the CFR sections instead of "verbatim"

The text in each CFR file was prepared from a model's training data, not
copy-pasted from the official eCFR HTML. That means structure, substance,
defined terms, dollar thresholds, and section numbering are accurate
post-2024-final-rule (89 FR 30046, effective October 1, 2024), but exact
wording may diverge in places from the eCFR text. The substance an
auditor or pass-through monitor would consider material — what's required,
who must do it, when, and at what threshold — is preserved.

Before treating any agent output as authoritative for federal grant
work, a human (Krista, Ritu, or counsel) should compare the cited
regulatory excerpt to the official eCFR text. The agent's prompts (in
`prompts.py`, separate file) enforce this: they instruct the model to
mark every quotation as "per training-data corpus; verify against eCFR".

To upgrade a file from `structured-paraphrase` to `verbatim`:

1. Open the source URL in the file's header.
2. Compare the file's body text to the eCFR text.
3. Replace the body with the eCFR text exactly (preserving paragraph
   structure and subsection enumeration).
4. Update the file's `VERIFICATION:` field to `verbatim`.
5. Update `manifest.json` to match.
6. Commit with a message naming the section verified.

A future v1.1 enhancement may automate this against the eCFR API.

## How the agent uses this corpus

`corpus.py` (sibling of this directory in
`src/grant_compliance/compliance_requirements_agent/corpus.py`) loads the
manifest, reads each file, parses the header, and exposes the corpus to
the agent's prompts. The agent's Mode A prompt (in `prompts.py`)
includes the corpus body text and instructs the model to:

- Generate requirements grounded only in the corpus
- Cite the specific CFR section for every requirement
- Use only the verbatim and structured-paraphrase text — never invent text
- Flag any topic where the corpus has skeleton-only coverage as outside
  the agent's reliable scope

The agent's Mode B prompt has the same constraints. Outputs that violate
them are rejected at validation in `agent.py`.

## v1.1 follow-ups (visible gaps in v1)

These are tracked in `manifest.json` under `v1_1_followups` so they're
machine-readable and won't get lost.

1. **Populate the OMB Compliance Supplement Part 4-11.300 skeleton.**
   PRIORITY: HIGH. The file at
   `omb_compliance_supplement_2025/part_4_11.300_economic_development_cluster.txt`
   is currently a structural skeleton, not content — it documents what
   should exist but does not contain citable text. The agent honors this
   by refusing to cite skeleton files and surfacing an explicit
   "outside-current-corpus" caveat for 11.307-program-specific questions.
   For the v1 launch (Phouang counsel review), this is acceptable because
   the review is grounded in 2 CFR 200 sections that ARE covered. For the
   June 2026 ESD-WMU annual monitoring engagement, the Compliance
   Supplement's program-specific Special Tests and Provisions are the
   audit framework ESD applies — populating this file is the highest-value
   corpus upgrade before that engagement. Populate by downloading the
   2025 OMB Compliance Supplement PDF from whitehouse.gov, navigating to
   Part 4 / Department of Commerce / Assistance Listing 11.307, and
   transcribing the relevant text. The skeleton file itself has the
   step-by-step protocol.

2. **Upgrade the remaining 13 CFR files from `structured-paraphrase` to
   `verbatim`.** PRIORITY: MEDIUM. Currently §§200.319 and 200.318(c)
   are the only verbatim CFR text in the corpus — they were upgraded
   ahead of v1 because they're most central to the Phouang counsel
   review. The other 13 files are accurate to the substance and
   structure of the post-2024-final-rule text, but exact wording may
   diverge from the official source. The agent's prompts include a
   "per training-data corpus; verify against eCFR" disclaimer for
   non-verbatim sections to keep the honesty discipline intact. Upgrade
   each file individually following the protocol below.

## Updating the corpus

The 2 CFR 200 regulations evolve. The OMB Compliance Supplement is
republished annually (typically May–August). To update the corpus:

1. Identify which sections changed.
2. Update the affected text files, updating `EFFECTIVE_DATE`, `LAST_UPDATED`,
   and `NOTES` in the header.
3. Update the `version` field in `manifest.json`.
4. Generate a new `ComplianceRequirementsSet` (Mode A run) so requirements
   reflect the updated regulation; the prior set is preserved as
   `superseded_by` per the spec.
5. Commit with a message naming the rule change (e.g., "corpus: 2025
   final rule §200.319 amendments").
