"""
Steps 8-10: Migrate BACPAC reference data to PostgreSQL.

BCP files are SQL Server binary format. For reference tables we parse
the model.xml schema and attempt BCP text extraction. For tables that
can't be parsed from BCP, we use the skills table (already migrated)
cross-references.

Strategy:
- CIP codes: parse from BCP (text-heavy, likely extractable)
- SOC codes: parse from BCP
- CIP-SOC crosswalk: parse from BCP (UUID pairs)
- edu_providers: parse from BCP
- Rating tables: minimal data, extract what we can
"""
import os, re, struct, json, psycopg2, uuid
from pgconfig import PG_CONFIG

BACPAC_DATA = "C:/Users/ritub/projects/wfd-os/recovered-code/bacpac/extracted/Data"


def extract_utf16_strings(filepath, min_length=3):
    """Extract UTF-16LE strings from a BCP file."""
    with open(filepath, "rb") as f:
        data = f.read()

    strings = []
    current = []
    i = 0
    while i < len(data) - 1:
        # Check for UTF-16LE character (printable ASCII range)
        byte1 = data[i]
        byte2 = data[i + 1]
        if byte2 == 0 and 32 <= byte1 <= 126:
            current.append(chr(byte1))
            i += 2
        else:
            if len(current) >= min_length:
                strings.append("".join(current))
            current = []
            i += 1

    if len(current) >= min_length:
        strings.append("".join(current))

    return strings


def extract_guids(filepath):
    """Extract 16-byte GUIDs from BCP file."""
    with open(filepath, "rb") as f:
        data = f.read()

    guids = []
    # GUIDs in BCP are 16 bytes in mixed-endian format
    i = 0
    while i <= len(data) - 16:
        try:
            # Try to parse as UUID
            raw = data[i:i+16]
            # SQL Server GUID format: first 3 groups little-endian, last 2 big-endian
            u = uuid.UUID(bytes_le=raw)
            # Filter out obviously invalid GUIDs
            s = str(u)
            if s != "00000000-0000-0000-0000-000000000000":
                guids.append(s)
                i += 16
                continue
        except:
            pass
        i += 1

    return guids


def migrate_cip_codes(conn):
    """Parse CIP taxonomy from BCP."""
    print("\n=== Migrating CIP codes ===")
    bcp_path = os.path.join(BACPAC_DATA, "dbo.cip", "TableData-000-00000.BCP")

    if not os.path.exists(bcp_path):
        print("  BCP file not found!")
        return

    strings = extract_utf16_strings(bcp_path, min_length=3)
    print(f"  Extracted {len(strings)} strings from BCP")

    # CIP codes follow pattern: XX.XXXX
    cip_pattern = re.compile(r'^\d{2}\.\d{4}$')

    # Group strings: code followed by title followed by definition
    cur = conn.cursor()
    inserted = 0

    # Strategy: find CIP codes, then grab the next string as the title
    i = 0
    while i < len(strings):
        s = strings[i].strip()
        if cip_pattern.match(s):
            code = s
            title = strings[i + 1].strip() if i + 1 < len(strings) else None
            # Skip if title looks like another code
            if title and cip_pattern.match(title):
                title = None

            if title and len(title) > 3:
                try:
                    cur.execute(
                        "INSERT INTO cip_codes (code, title) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                        (code, title[:500])
                    )
                    inserted += 1
                except Exception as e:
                    conn.rollback()
                    pass
            i += 2
        else:
            i += 1

    conn.commit()
    print(f"  Inserted: {inserted} CIP codes")


def migrate_soc_codes(conn):
    """Parse SOC codes from BCP files (all 3 versions)."""
    print("\n=== Migrating SOC codes ===")

    soc_tables = [
        ("dbo.socc", "current"),
        ("dbo.socc_2010", "2010"),
        ("dbo.socc_2018", "2018"),
    ]

    cur = conn.cursor()
    total_inserted = 0

    for table_name, version in soc_tables:
        bcp_path = os.path.join(BACPAC_DATA, table_name, "TableData-000-00000.BCP")
        if not os.path.exists(bcp_path):
            print(f"  {table_name}: BCP not found")
            continue

        strings = extract_utf16_strings(bcp_path, min_length=2)
        print(f"  {table_name}: extracted {len(strings)} strings")

        # SOC codes follow pattern: XX-XXXX or XX-XXXX.XX
        soc_pattern = re.compile(r'^\d{2}-\d{4}(\.\d{2})?$')
        inserted = 0

        i = 0
        while i < len(strings):
            s = strings[i].strip()
            if soc_pattern.match(s):
                code = s
                title = strings[i + 1].strip() if i + 1 < len(strings) else None
                if title and soc_pattern.match(title):
                    title = None

                if title and len(title) > 2:
                    try:
                        cur.execute(
                            "INSERT INTO soc_codes (code, title, version) VALUES (%s, %s, %s)",
                            (code, title[:500], version)
                        )
                        inserted += 1
                    except:
                        conn.rollback()
                i += 2
            else:
                i += 1

        conn.commit()
        total_inserted += inserted
        print(f"  {table_name} ({version}): inserted {inserted}")

    print(f"  Total SOC codes: {total_inserted}")


def migrate_edu_providers(conn):
    """Parse edu_providers from BCP."""
    print("\n=== Migrating edu_providers -> colleges ===")
    bcp_path = os.path.join(BACPAC_DATA, "dbo.edu_providers", "TableData-000-00000.BCP")

    if not os.path.exists(bcp_path):
        print("  BCP not found!")
        return

    strings = extract_utf16_strings(bcp_path, min_length=3)
    print(f"  Extracted {len(strings)} strings")

    # edu_providers have: name, website, city, state, type
    # Filter for institution-like names (exclude URLs, short codes, etc.)
    cur = conn.cursor()
    inserted = 0

    # Look for patterns: strings that look like institution names
    # (contain "University", "College", "Institute", "School", etc.)
    edu_keywords = ["university", "college", "institute", "school",
                    "academy", "center", "community", "technical",
                    "polytechnic", "seminary"]

    seen_names = set()
    for s in strings:
        s_lower = s.lower().strip()
        if any(kw in s_lower for kw in edu_keywords) and len(s) > 5 and s not in seen_names:
            seen_names.add(s)
            try:
                cur.execute(
                    """INSERT INTO colleges (name, source_system, original_record_id)
                       VALUES (%s, %s, %s)""",
                    (s[:255], "bacpac", f"edu_provider_{s[:100]}")
                )
                inserted += 1
            except:
                conn.rollback()

    conn.commit()
    print(f"  Inserted: {inserted} colleges from edu_providers")


def migrate_rating_tables(conn):
    """Extract career pathway assessment data from rating tables."""
    print("\n=== Migrating rating tables -> career_pathway_assessments ===")

    rating_tables = [
        ("dbo.BrandingRating", "Personal Branding"),
        ("dbo.CybersecurityRating", "Cybersecurity"),
        ("dbo.DataAnalyticsRating", "Data Analytics"),
        ("dbo.DurableSkillsRating", "Durable Skills"),
        ("dbo.ITCloudRating", "IT Cloud"),
        ("dbo.SoftwareDevRating", "Software Development"),
    ]

    cur = conn.cursor()
    total = 0

    for table_name, pathway in rating_tables:
        bcp_path = os.path.join(BACPAC_DATA, table_name, "TableData-000-00000.BCP")
        if not os.path.exists(bcp_path):
            continue

        file_size = os.path.getsize(bcp_path)
        if file_size < 100:
            print(f"  {pathway}: empty/minimal ({file_size} bytes)")
            continue

        # Extract what data we can
        strings = extract_utf16_strings(bcp_path, min_length=2)
        guids = extract_guids(bcp_path)

        if guids:
            # First GUID is likely the record ID, second might be student FK
            # Store as a reference record
            try:
                cur.execute(
                    """INSERT INTO career_pathway_assessments
                       (pathway, scores, assessed_at)
                       VALUES (%s, %s, NOW())""",
                    (pathway, json.dumps({
                        "source": "bacpac_bcp",
                        "raw_guids_count": len(guids),
                        "raw_strings_count": len(strings),
                        "sample_strings": strings[:10],
                        "note": "Extracted from BCP binary. Needs SQL Server restore for full data."
                    }))
                )
                total += 1
            except:
                conn.rollback()

        print(f"  {pathway}: {file_size} bytes, {len(guids)} GUIDs, {len(strings)} strings")

    conn.commit()
    print(f"  Total assessment placeholders: {total}")


def main():
    print("=" * 60)
    print("Steps 8-10: BACPAC Reference Data Migration")
    print("=" * 60)

    conn = psycopg2.connect(**PG_CONFIG)

    try:
        migrate_cip_codes(conn)        # Step 9a
        migrate_soc_codes(conn)        # Step 9b
        migrate_edu_providers(conn)    # Step 10
        migrate_rating_tables(conn)    # Step 11
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("BACPAC reference data migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
