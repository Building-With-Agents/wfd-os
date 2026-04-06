# TODO — Student Re-engagement Campaign
**Status:** BLOCKED — waiting on Student Portal
**Priority:** High (3,636 students with no resume)
**Owner:** Orchestrator Agent + Marketing Agent

---

## Prerequisite: Student Portal Must Be Built First

DO NOT contact students until the Student Portal is live.
There must be somewhere to send them before any outreach begins.

**Deliberate sequence:**
1. Agents (Profile, Career Services) — built first
2. Student Portal — built and deployed
3. Re-engagement campaign — only AFTER portal is live

---

## The Problem

- 3,636 students (77% of 4,727) have no resume in Blob Storage
- These students are in PostgreSQL with migration tags but
  incomplete profiles (no resume, no parsed skills, no education)
- Profile completeness scores are 20-40% for most of them
- They cannot reach Talent Showcase eligibility without a resume

---

## The Campaign

Once Student Portal is live:

1. **Tag eligible students** — all records where:
   - `resume_blob_path IS NULL`
   - `email IS NOT NULL`
   - `pipeline_status NOT IN ('placed', 'alumni', 'dropped_out')`
   - Mark: `re_engagement_eligible = TRUE`

2. **Marketing Agent sends personalized email** to each:
   - Explain Waifinder value proposition
   - Show what CFA can do for them (matching, career services, showcase)
   - Include tokenized link to Student Portal for resume upload
   - No password needed — tokenized link auth per CLAUDE.md spec

3. **On resume upload:**
   - Career Services Agent auto-parses resume via Claude API
   - Profile Agent updates student record and recalculates completeness
   - Orchestrator routes to intake queue for CFA staff review
   - Student gets confirmation + next steps via Student Portal

4. **Track re-engagement outcomes:**
   - `re_engagement_status`: sent, opened, clicked, uploaded, enrolled
   - Measure conversion rate at each step
   - Flag students who don't respond after 2 attempts

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Emails delivered | 3,636 (all eligible) |
| Resume upload rate | >= 15% within 30 days |
| Profile completeness improvement | 20-40% → 60-80% for uploaders |
| New showcase-eligible students | >= 200 from re-engagement |

---

## Dependencies

| Dependency | Status |
|------------|--------|
| Profile Agent | Built (resume parsing working) |
| Career Services Agent | Not started |
| Student Portal | Not started |
| Marketing Agent / email system | Not started |
| Azure Communication Services | Live on thewaifinder.com |

---

*Do not start this campaign until Student Portal is deployed and tested.*
