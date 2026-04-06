# TODO — Gap Analysis Further Tuning
**Status:** DEFERRED — revisit after all initial agents are built
**Priority:** Medium (functional now, optimize later with real data)
**Owner:** Career Services Agent + Cohort 1 apprentices

---

## Current State

- Average gap score: 26.5 (up from 7.8 after core skills normalization)
- Core skills threshold: 15 per job
- Matching: exact + normalized + semantic (cosine >= 0.75)
- Scores are realistic but not yet validated against outcomes

---

## Tuning Considerations (Do NOT implement yet)

1. **Weight skills by market demand frequency**
   - Skills appearing in 20%+ of job listings should count more
   - Use the skills demand report data to set weights
   - E.g., Python (19.4% of jobs) weighted higher than Apache Thrift

2. **Separate must-have vs nice-to-have gap scores**
   - Must-have: first 5-7 core skills (title-defining skills)
   - Nice-to-have: remaining core skills
   - Two scores: must_have_gap and nice_to_have_gap
   - Showcase eligibility could use must_have_gap only

3. **Adjust core skills threshold per job category**
   - Entry-level roles: top 8-10 skills
   - Senior roles: top 15-20 skills
   - Specialist roles: top 5-8 skills (fewer but deeper)
   - Use job title keywords to classify

4. **Incorporate BLS occupational data**
   - BLS OEWS data provides employment levels by occupation
   - Use as validation: high-employment occupations should have
     well-calibrated gap scores
   - MSA code 21340 (El Paso) for Borderplex-specific weighting

5. **A/B test against placement outcomes**
   - Once Placement Agent is tracking Stage 6-7 data:
     - Did students with higher gap scores get placed faster?
     - Which missing skills actually blocked placement?
     - Which upskilling recommendations led to placement?
   - This is the real validation — gap scores should predict
     placement probability

6. **Cohort 1 apprentice OJT project**
   - Gap analysis tuning is an excellent OJT deliverable
   - Apprentices can: analyze placement data, build regression
     model, tune weights, measure prediction accuracy
   - Supervised by Gary as Waifinder Client 0 work

---

## When to Revisit

- AFTER all initial agents are built and running
- AFTER Student Portal is live and collecting data
- AFTER at least 50 placements are tracked with outcomes
- AFTER Reporting Agent can surface outcome correlations
- Don't over-optimize before real placement data exists

---

*Functional gap analysis is better than perfect gap analysis
that never ships. Ship now, tune with data later.*
