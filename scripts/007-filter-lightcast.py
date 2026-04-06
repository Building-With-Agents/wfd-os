"""
Apply digital role filter retroactively to 2,670 Lightcast seed jobs.
Uses blocklist/allowlist/keywords only (no LLM).
"""
import sys, os, psycopg2
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
    "../agents/market-intelligence/ingest"))
sys.path.insert(0, os.path.dirname(__file__))
from pgconfig import PG_CONFIG
from digital_filter import filter_digital_role


def main():
    print("=== Applying digital filter to Lightcast jobs ===\n")

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Get all Lightcast jobs
    cur.execute("""
        SELECT id, title, description, legacy_data->>'cfa_skills' as skills_text
        FROM job_listings
        WHERE source = 'lightcast'
    """)
    jobs = cur.fetchall()
    print(f"Processing {len(jobs)} Lightcast jobs...\n")

    stats = {
        "blocklist": 0,
        "allowlist": 0,
        "keywords": 0,
        "keywords_weak": 0,
        "ambiguous": 0,
        "no_title": 0,
    }
    digital_count = 0
    non_digital_count = 0

    for job_id, title, description, skills_text in jobs:
        # Combine description + skills for keyword matching
        full_desc = (description or "") + " " + (skills_text or "")
        result = filter_digital_role(title, full_desc)

        layer = result["filter_layer"]
        stats[layer] = stats.get(layer, 0) + 1

        if result["is_digital"]:
            digital_count += 1
        elif result["is_digital"] is False:
            non_digital_count += 1

        cur.execute("""
            UPDATE job_listings
            SET is_digital = %s,
                digital_filter_layer = %s
            WHERE id = %s
        """, (result["is_digital"], layer, job_id))

    conn.commit()

    # Print results
    print("Filter Results:")
    print("-" * 50)
    for layer, count in sorted(stats.items(), key=lambda x: -x[1]):
        pct = count / len(jobs) * 100
        bar = "#" * (count // 20)
        print(f"  {layer:15s}: {count:5d} ({pct:5.1f}%) {bar}")

    print(f"\nSummary:")
    print(f"  Digital roles:     {digital_count} ({digital_count/len(jobs)*100:.1f}%)")
    print(f"  Non-digital:       {non_digital_count} ({non_digital_count/len(jobs)*100:.1f}%)")
    ambig = len(jobs) - digital_count - non_digital_count
    print(f"  Ambiguous:         {ambig} ({ambig/len(jobs)*100:.1f}%)")

    # Show sample digital jobs
    cur.execute("""
        SELECT title, company_name, city, state, digital_filter_layer
        FROM job_listings
        WHERE source = 'lightcast' AND is_digital = TRUE
        ORDER BY random() LIMIT 10
    """)
    print(f"\nSample DIGITAL jobs:")
    for title, company, city, state, layer in cur.fetchall():
        loc = f"{city or '?'}, {state or '?'}"
        print(f"  [{layer:10s}] {title[:50]:50s} | {loc}")

    # Show sample non-digital
    cur.execute("""
        SELECT title, company_name, digital_filter_layer
        FROM job_listings
        WHERE source = 'lightcast' AND is_digital = FALSE
        ORDER BY random() LIMIT 5
    """)
    print(f"\nSample NON-DIGITAL jobs (correctly filtered out):")
    for title, company, layer in cur.fetchall():
        print(f"  [{layer:10s}] {title[:60]}")

    conn.close()


if __name__ == "__main__":
    main()
