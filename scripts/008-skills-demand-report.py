"""
Generate skills demand report from Lightcast job listings.
Parses the cfa_skills field (comma-separated) from legacy_data.
First output for Alma at Workforce Solutions Borderplex.
"""
import sys, os, psycopg2, json
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from pgconfig import PG_CONFIG


def main():
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Get all digital Lightcast jobs with skills
    cur.execute("""
        SELECT title, legacy_data->>'cfa_skills' as skills_text,
               legacy_data->>'cfa_location' as location,
               company_name
        FROM job_listings
        WHERE source = 'lightcast'
          AND (is_digital = TRUE OR is_digital IS NULL)
          AND legacy_data->>'cfa_skills' IS NOT NULL
    """)
    jobs = cur.fetchall()

    print("=" * 70)
    print("SKILLS DEMAND REPORT")
    print("Waifinder Market Intelligence -- JIE Deployment 001")
    print("For: Workforce Solutions Borderplex (Alma)")
    print(f"Data source: Lightcast Q3-Q4 2024 ({len(jobs)} digital job listings)")
    print("=" * 70)

    # Count skills across all jobs
    skill_counter = Counter()
    job_count_per_skill = Counter()
    total_jobs = len(jobs)

    for title, skills_text, location, company in jobs:
        if not skills_text:
            continue
        skills = [s.strip() for s in skills_text.split(",") if s.strip()]
        seen = set()
        for skill in skills:
            skill_counter[skill] += 1
            if skill not in seen:
                job_count_per_skill[skill] += 1
                seen.add(skill)

    # Top 20 skills by number of job listings mentioning them
    top_20 = job_count_per_skill.most_common(20)

    print(f"\n{'='*70}")
    print("TOP 20 MOST IN-DEMAND SKILLS")
    print(f"(by number of job listings mentioning the skill)")
    print(f"{'='*70}\n")
    print(f"{'Rank':>4} {'Skill':<45} {'Jobs':>6} {'% of Jobs':>10}")
    print("-" * 70)
    for i, (skill, count) in enumerate(top_20, 1):
        pct = count / total_jobs * 100
        bar = "#" * int(pct / 2)
        print(f"{i:>4}. {skill:<45} {count:>6} {pct:>9.1f}% {bar}")

    # Category analysis — group skills into categories
    print(f"\n{'='*70}")
    print("SKILLS BY CATEGORY")
    print(f"{'='*70}\n")

    categories = {
        "Programming Languages": [
            "Python", "Java", "JavaScript", "C#", "C++", "TypeScript",
            "SQL", "R", "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin",
        ],
        "Cloud & Infrastructure": [
            "Amazon Web Services", "Microsoft Azure", "Google Cloud",
            "Kubernetes", "Docker", "Terraform", "Jenkins", "CI/CD",
            "Linux", "DevOps", "Cloud Computing",
        ],
        "Data & Analytics": [
            "Data Analysis", "Data Science", "Machine Learning",
            "Data Warehousing", "Business Intelligence", "Tableau",
            "Power BI", "Data Mining", "Statistics", "Big Data",
            "Apache Spark", "Data Engineering",
        ],
        "Security": [
            "Network Security", "Cyber Security", "Information Security",
            "Encryption", "Firewall", "Security Operations",
            "Vulnerability Assessment", "Penetration Testing",
        ],
        "Project & Process": [
            "Project Management", "Agile Methodology", "Scrum",
            "JIRA", "Product Management", "Lean",
        ],
    }

    for cat_name, cat_skills in categories.items():
        matches = []
        for cs in cat_skills:
            cs_lower = cs.lower()
            for skill, count in job_count_per_skill.items():
                if cs_lower in skill.lower() or skill.lower() in cs_lower:
                    matches.append((skill, count))
                    break
        matches.sort(key=lambda x: -x[1])
        if matches:
            total_cat = sum(c for _, c in matches)
            print(f"  {cat_name} ({total_cat} total mentions):")
            for skill, count in matches[:5]:
                pct = count / total_jobs * 100
                print(f"    {skill:<40} {count:>5} ({pct:.1f}%)")
            print()

    # Top employers by posting volume
    print(f"{'='*70}")
    print("TOP 15 EMPLOYERS BY POSTING VOLUME")
    print(f"{'='*70}\n")

    cur.execute("""
        SELECT company_name, count(*) as postings,
               count(*) FILTER (WHERE is_digital = TRUE) as digital_postings
        FROM job_listings
        WHERE source = 'lightcast' AND company_name IS NOT NULL
        GROUP BY company_name
        ORDER BY count(*) DESC
        LIMIT 15
    """)
    print(f"{'Rank':>4} {'Employer':<45} {'Total':>6} {'Digital':>8}")
    print("-" * 70)
    for i, (company, total, digital) in enumerate(cur.fetchall(), 1):
        name = company[:44] if company else "Unknown"
        print(f"{i:>4}. {name:<45} {total:>6} {digital:>8}")

    # Location distribution
    print(f"\n{'='*70}")
    print("TOP 10 LOCATIONS")
    print(f"{'='*70}\n")

    cur.execute("""
        SELECT
            COALESCE(city, legacy_data->>'cfa_location', 'Unknown') as loc,
            count(*) as jobs
        FROM job_listings
        WHERE source = 'lightcast' AND (is_digital = TRUE OR is_digital IS NULL)
        GROUP BY loc
        ORDER BY count(*) DESC
        LIMIT 10
    """)
    for loc, count in cur.fetchall():
        pct = count / total_jobs * 100
        print(f"  {loc:<40} {count:>5} ({pct:.1f}%)")

    # Summary stats
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}\n")
    print(f"  Total job listings analyzed:      {total_jobs}")
    print(f"  Unique skills identified:         {len(job_count_per_skill)}")
    print(f"  Avg skills per listing:           {sum(skill_counter.values()) / total_jobs:.1f}")
    print(f"  Digital role rate:                 {total_jobs}/{2670} = {total_jobs/2670*100:.1f}%")

    # Skills gap indicator
    print(f"\n{'='*70}")
    print("SKILLS WITH HIGHEST DEMAND (potential gap indicators)")
    print("These skills appear in 10%+ of digital job listings")
    print(f"{'='*70}\n")

    high_demand = [(s, c) for s, c in job_count_per_skill.most_common(50)
                   if c / total_jobs >= 0.10]
    for skill, count in high_demand:
        pct = count / total_jobs * 100
        print(f"  {skill:<45} {count:>5} ({pct:.1f}%)")

    conn.close()

    print(f"\n{'='*70}")
    print("Report generated. This is JIE Deployment 001 output for WSB.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
