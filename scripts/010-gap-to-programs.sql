-- Which college programs best match the most common skill gaps
-- from gap_analyses?

-- Step 1: Find most common missing skills across all gap analyses
WITH missing_skills AS (
    SELECT unnest(missing_skills) as skill_name, count(*) as gap_count
    FROM gap_analyses
    GROUP BY unnest(missing_skills)
    ORDER BY count(*) DESC
    LIMIT 20
),

-- Step 2: Find skills in taxonomy that match (normalized)
skill_matches AS (
    SELECT ms.skill_name as gap_skill,
           ms.gap_count,
           s.skill_id,
           s.skill_name as taxonomy_skill
    FROM missing_skills ms
    JOIN skills s ON LOWER(s.skill_name) = LOWER(ms.skill_name)
       OR LOWER(REGEXP_REPLACE(s.skill_name, '\s*\([^)]*\)', '', 'g')) = LOWER(ms.skill_name)
),

-- Step 3: Find programs that teach these skills
program_matches AS (
    SELECT sm.gap_skill,
           sm.gap_count,
           cp.name as program_name,
           cp.source as program_source,
           sm.taxonomy_skill
    FROM skill_matches sm
    JOIN program_skills ps ON ps.skill_id = sm.skill_id
    JOIN college_programs cp ON cp.id = ps.program_id
)

SELECT gap_skill,
       gap_count as students_missing,
       program_name,
       program_source
FROM program_matches
ORDER BY gap_count DESC, gap_skill, program_name
LIMIT 50;
