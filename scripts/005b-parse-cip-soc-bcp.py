"""
Parse CIP and SOC codes from BCP binary files.
BCP format: length-prefixed UTF-16LE strings separated by control bytes.
"""
import psycopg2, re, os
from pgconfig import PG_CONFIG

BACPAC_DATA = "C:/Users/ritub/projects/wfd-os/recovered-code/bacpac/extracted/Data"


def parse_bcp_utf16_records(filepath):
    """Parse BCP file as a sequence of length-prefixed UTF-16LE strings.
    Returns list of lists (each inner list = one record's string fields)."""
    with open(filepath, "rb") as f:
        data = f.read()

    # Extract all UTF-16LE strings by scanning for runs of (byte, 0x00) pairs
    all_strings = []
    current = []
    i = 0
    while i < len(data) - 1:
        b1 = data[i]
        b2 = data[i + 1]
        if b2 == 0 and 32 <= b1 <= 126:
            current.append(chr(b1))
            i += 2
        elif b2 == 0 and b1 in (9, 10, 13):  # tab, newline, cr
            current.append(chr(b1))
            i += 2
        else:
            if current:
                s = "".join(current).strip()
                if s:
                    all_strings.append(s)
                current = []
            i += 1

    if current:
        s = "".join(current).strip()
        if s:
            all_strings.append(s)

    return all_strings


def migrate_cip(conn):
    """Parse CIP codes: format is code + title + definition."""
    print("\n=== Parsing CIP codes from BCP ===")
    bcp_path = os.path.join(BACPAC_DATA, "dbo.cip", "TableData-000-00000.BCP")
    strings = parse_bcp_utf16_records(bcp_path)
    print(f"  Extracted {len(strings)} strings")
    print(f"  First 10: {strings[:10]}")

    # CIP codes are 2-digit or 2-digit.4-digit
    # The BCP appears to store: code, title, definition in sequence
    # But code might be just "01" not "01.0000"
    cur = conn.cursor()
    cur.execute("DELETE FROM cip_codes")  # Clean slate

    inserted = 0
    # Walk through strings looking for short numeric codes followed by text
    i = 0
    while i < len(strings):
        s = strings[i]
        # Check if this looks like a CIP code (2-digit, possibly with dot)
        if re.match(r'^\d{1,2}(\.\d{1,4})?$', s):
            code = s
            # Pad to standard format
            if '.' not in code:
                code = code.zfill(2)
            else:
                parts = code.split('.')
                code = parts[0].zfill(2) + '.' + parts[1].ljust(4, '0')

            # Next string should be the title
            title = None
            definition = None
            if i + 1 < len(strings) and not re.match(r'^\d{1,2}(\.\d{1,4})?$', strings[i+1]):
                title = strings[i + 1][:500]
                # Check if there's a definition after that
                if (i + 2 < len(strings) and
                    not re.match(r'^\d{1,2}(\.\d{1,4})?$', strings[i+2]) and
                    len(strings[i+2]) > len(title)):
                    definition = strings[i + 2]
                    i += 3
                else:
                    i += 2
            else:
                i += 1
                continue

            try:
                cur.execute(
                    "INSERT INTO cip_codes (code, title, definition) VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING",
                    (code, title, definition)
                )
                inserted += 1
            except Exception as e:
                conn.rollback()
                print(f"  Error inserting CIP {code}: {e}")
        else:
            i += 1

    conn.commit()
    print(f"  Inserted: {inserted} CIP codes")

    # Show sample
    cur.execute("SELECT code, title FROM cip_codes ORDER BY code LIMIT 5")
    print("  Sample:")
    for code, title in cur.fetchall():
        print(f"    {code}: {title[:80]}")


def migrate_soc(conn):
    """Parse SOC codes from all 3 version tables."""
    print("\n=== Parsing SOC codes from BCP ===")

    soc_tables = [
        ("dbo.socc", "current"),
        ("dbo.socc_2010", "2010"),
        ("dbo.socc_2018", "2018"),
    ]

    cur = conn.cursor()
    cur.execute("DELETE FROM soc_codes")  # Clean slate
    total = 0

    for table_name, version in soc_tables:
        bcp_path = os.path.join(BACPAC_DATA, table_name, "TableData-000-00000.BCP")
        if not os.path.exists(bcp_path):
            print(f"  {table_name}: not found")
            continue

        strings = parse_bcp_utf16_records(bcp_path)
        print(f"  {table_name}: {len(strings)} strings, first 5: {strings[:5]}")

        inserted = 0
        i = 0
        while i < len(strings):
            s = strings[i]
            # SOC codes: XX-XXXX or XX-XXXX.XX
            if re.match(r'^\d{2}-\d{4}(\.\d{2})?$', s):
                code = s
                title = None
                if i + 1 < len(strings) and not re.match(r'^\d{2}-\d{4}', strings[i+1]):
                    title = strings[i + 1][:500]
                    i += 2
                else:
                    i += 1
                    continue

                try:
                    cur.execute(
                        "INSERT INTO soc_codes (code, title, version) VALUES (%s, %s, %s)",
                        (code, title, version)
                    )
                    inserted += 1
                except:
                    conn.rollback()
            else:
                i += 1

        conn.commit()
        total += inserted
        print(f"  {table_name} ({version}): inserted {inserted}")

    print(f"  Total SOC codes: {total}")

    cur.execute("SELECT code, title, version FROM soc_codes ORDER BY version, code LIMIT 5")
    print("  Sample:")
    for code, title, ver in cur.fetchall():
        print(f"    [{ver}] {code}: {title[:80]}")


def main():
    print("=" * 60)
    print("BCP Reference Data Parser (CIP + SOC)")
    print("=" * 60)

    conn = psycopg2.connect(**PG_CONFIG)
    try:
        migrate_cip(conn)
        migrate_soc(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
