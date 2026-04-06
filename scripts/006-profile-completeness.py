"""
Calculate profile completeness scores for all students.

Uses the model from CLAUDE.md:
- Required fields (70% weight): full_name, email, skills (3+),
  education (institution + degree), location, availability_status, resume_file
- Preferred fields (30% weight): phone, linkedin_url, graduation_year,
  field_of_study, project_highlights, career_objective,
  expected_salary_range, work_authorization, certifications
- showcase_eligible = required_fields_complete == 1.0
"""
import psycopg2, json
from pgconfig import PG_CONFIG


def calculate_completeness(conn):
    print("=== Calculating profile completeness for all students ===\n")

    cur = conn.cursor()

    # Get all students
    cur.execute("SELECT id, full_name, email, phone, institution, degree, "
                "field_of_study, graduation_year, city, state, zipcode, "
                "linkedin_url, github_url, portfolio_url, "
                "resume_blob_path, resume_parsed, "
                "availability_status, work_authorization, "
                "expected_salary_range, legacy_data "
                "FROM students")

    students = cur.fetchall()
    print(f"Processing {len(students)} students...\n")

    # Also check how many skills each student has
    cur.execute("""
        SELECT student_id, count(*) as skill_count
        FROM student_skills
        GROUP BY student_id
    """)
    skill_counts = dict(cur.fetchall())

    updated = 0
    completeness_dist = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    showcase_eligible_count = 0

    for row in students:
        (sid, full_name, email, phone, institution, degree,
         field_of_study, graduation_year, city, state, zipcode,
         linkedin_url, github_url, portfolio_url,
         resume_blob_path, resume_parsed,
         availability_status, work_authorization,
         expected_salary_range, legacy_data) = row

        # Check legacy_data for additional fields
        legacy = {}
        if legacy_data:
            if isinstance(legacy_data, str):
                try:
                    legacy = json.loads(legacy_data)
                except:
                    legacy = {}
            elif isinstance(legacy_data, dict):
                legacy = legacy_data

        # Check for skills in legacy tech_skills_selfassessment
        has_skills_legacy = False
        tech_skills = legacy.get("tech_skills_selfassessment", {})
        if tech_skills and len(tech_skills) >= 3:
            has_skills_legacy = True

        skill_count = skill_counts.get(sid, 0)
        has_skills = skill_count >= 3 or has_skills_legacy

        # Check for email in legacy
        if not email:
            email = legacy.get("cfa_email") or legacy.get("emailaddress1")

        # Check for location
        has_location = bool(city or state or zipcode)

        # Check for education
        has_education = bool(institution and degree)
        # Also check legacy for education info
        if not has_education:
            legacy_school = (legacy.get("cfa_nameofhighschool") or
                            legacy.get("cfa_cityschoolcollege") or
                            legacy.get("cfa_form_trainingschoolname"))
            if legacy_school:
                has_education = True  # Has at least institution

        # Check resume — also look for blob path pattern in contact ID
        has_resume = bool(resume_blob_path)

        # --- REQUIRED FIELDS (7 checks) ---
        required_checks = {
            "full_name": bool(full_name),
            "email": bool(email),
            "skills_3plus": has_skills,
            "education": has_education,
            "location": has_location,
            "availability_status": bool(availability_status),
            "resume_file": has_resume,
        }

        required_met = sum(1 for v in required_checks.values() if v)
        required_total = len(required_checks)
        required_complete = round(required_met / required_total, 2)

        missing_required = [k for k, v in required_checks.items() if not v]

        # --- PREFERRED FIELDS (9 checks) ---
        preferred_checks = {
            "phone": bool(phone),
            "linkedin_url": bool(linkedin_url),
            "graduation_year": bool(graduation_year),
            "field_of_study": bool(field_of_study),
            "project_highlights": False,  # Not currently tracked
            "career_objective": bool(legacy.get("cfa_futuregoals")),
            "expected_salary_range": bool(expected_salary_range),
            "work_authorization": bool(work_authorization),
            "certifications": bool(legacy.get("cfa_istechnicalcertifications")),
        }

        preferred_met = sum(1 for v in preferred_checks.values() if v)
        preferred_total = len(preferred_checks)
        preferred_complete = round(preferred_met / preferred_total, 2)

        missing_preferred = [k for k, v in preferred_checks.items() if not v]

        # --- COMPOSITE SCORE ---
        completeness_score = round(
            (required_complete * 0.70) + (preferred_complete * 0.30), 2
        )

        # --- SHOWCASE ELIGIBLE ---
        eligible = (required_complete == 1.0)
        if eligible:
            showcase_eligible_count += 1

        # --- DATA QUALITY ---
        if required_complete >= 0.8:
            data_quality = "complete"
        elif required_complete >= 0.5:
            data_quality = "partial"
        else:
            data_quality = "minimal"

        # Distribution tracking
        pct = completeness_score * 100
        if pct < 20:
            completeness_dist["0-20"] += 1
        elif pct < 40:
            completeness_dist["20-40"] += 1
        elif pct < 60:
            completeness_dist["40-60"] += 1
        elif pct < 80:
            completeness_dist["60-80"] += 1
        else:
            completeness_dist["80-100"] += 1

        # --- UPDATE ---
        try:
            cur.execute("""
                UPDATE students SET
                    required_fields_complete = %s,
                    preferred_fields_complete = %s,
                    profile_completeness_score = %s,
                    missing_required = %s,
                    missing_preferred = %s,
                    showcase_eligible = %s,
                    data_quality = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                required_complete,
                preferred_complete,
                completeness_score,
                missing_required,
                missing_preferred,
                eligible,
                data_quality,
                sid,
            ))
            updated += 1
        except Exception as e:
            print(f"  Error: {e}")
            conn.rollback()

    conn.commit()

    # Print summary
    print(f"Updated: {updated} / {len(students)} students\n")
    print("Profile Completeness Distribution:")
    print("-" * 40)
    for bucket, count in completeness_dist.items():
        bar = "#" * (count // 20)
        print(f"  {bucket}%: {count:>5} {bar}")
    print(f"\nShowcase eligible (all required fields): {showcase_eligible_count}")
    print(f"Showcase eligible rate: {showcase_eligible_count}/{len(students)} "
          f"= {showcase_eligible_count/len(students)*100:.1f}%")

    # Data quality summary
    cur.execute("""
        SELECT data_quality, count(*)
        FROM students
        GROUP BY data_quality
        ORDER BY count(*) DESC
    """)
    print("\nData Quality Distribution:")
    for dq, count in cur.fetchall():
        print(f"  {dq}: {count}")

    # Top missing required fields
    cur.execute("""
        SELECT unnest(missing_required) as field, count(*)
        FROM students
        WHERE missing_required IS NOT NULL
        GROUP BY field
        ORDER BY count(*) DESC
    """)
    print("\nMost Common Missing Required Fields:")
    for field, count in cur.fetchall():
        print(f"  {field}: {count} ({count/len(students)*100:.0f}%)")


def main():
    print("=" * 60)
    print("Profile Completeness Calculation")
    print("=" * 60)

    conn = psycopg2.connect(**PG_CONFIG)
    try:
        calculate_completeness(conn)
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("Completeness calculation done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
