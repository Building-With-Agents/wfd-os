# TODO — College Pipeline Agent Program Mapping
**Status:** PAUSED — confirm Azure OpenAI budget first
**Priority:** Medium (649 programs already mapped, sufficient for MVP)

---

## Current State

- 649 programs mapped to skills taxonomy (embedding-based)
- 6,473 program-skill links created
- 920 unique skills covered
- Mapping uses Azure OpenAI text-embedding-3-small API

## Remaining Work

- 4,020 programs still need embedding generation
  - 80 remaining CFA college programs (of 729)
  - 3,940 Career Bridge programs (none started)

## Budget Considerations

- Each program = 1 Azure OpenAI embedding API call
- Estimate cost BEFORE running full batch
- text-embedding-3-small pricing: ~$0.02 per 1M tokens
- ~20 tokens per program name = ~80K tokens total = ~$0.002
  (very cheap, but confirm budget allocation first)

## When Ready to Run

1. Confirm Azure OpenAI budget with Ritu
2. Run CFA college programs first (80 remaining)
3. Then Career Bridge programs (3,940) in batches of 500
4. Monitor costs after each batch
5. Full run command:
   ```
   cd C:\Users\ritub\projects\wfd-os
   python agents/college-pipeline/map_programs_to_skills.py
   ```

## Do NOT

- Run without budget confirmation
- Map all 3,940 Career Bridge programs in one shot
- Use a more expensive embedding model

---

*649 mapped programs are sufficient to prove the concept
and answer gap-to-program questions for the MVP.*
