# TODO — College Data Linking
**Status:** DEFERRED — build portal with available data first
**Priority:** High (needed before College Portal goes live to clients)

---

## Data Cleanup Needed

1. **Fix messy college names in colleges table:**
   - "College Bellevue College" -> "Bellevue College"
   - "College*North Seattle College" -> "North Seattle College"
   - "JTombolo Institute at Bellevue College" -> "Tombolo Institute at Bellevue College"
   - Remove description-length entries (paragraphs stored as names)
   - Strip BCP artifact prefixes (High school4, College, College*, etc.)

2. **Re-query Dataverse cfa_collegeprograms with institution lookup:**
   - Fetch with `_cfa_institution_value` GUID resolved
   - Map each program to its parent institution
   - Update `college_programs.college_id` with proper FK links
   - Currently: 0/4,669 programs linked to institutions

3. **LLM-assisted program-institution matching:**
   - For programs where Dataverse lookup fails
   - Use Claude to match generic program names to known institutions
   - Requires Anthropic API credits
   - Target: all 729 CFA college programs linked

4. **Career Bridge program linking (3,940 programs):**
   - These are WA state programs, not institution-specific
   - May not need institution linking
   - Consider keeping as "statewide" programs

## When to Do This

- AFTER Anthropic API credits are topped up
- AFTER initial College Portal MVP is validated with BC and NSC
- Cohort 1 apprentices can assist with data cleanup during OJT
