"""
Fixed parser for CIP and SOC codes.
CIP: codes like "010101" with title embedded after separator chars
SOC: codes like "111011" with title concatenated
"""
import psycopg2, re, os
from pgconfig import PG_CONFIG

BACPAC_DATA = "C:/Users/ritub/projects/wfd-os/recovered-code/bacpac/extracted/Data"


def read_utf16_strings(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    strings = []
    current = []
    i = 0
    while i < len(data) - 1:
        b1, b2 = data[i], data[i + 1]
        if b2 == 0 and (32 <= b1 <= 126 or b1 in (9, 10, 13)):
            current.append(chr(b1))
            i += 2
        else:
            if current:
                s = "".join(current).strip()
                if s:
                    strings.append(s)
                current = []
            i += 1
    if current:
        s = "".join(current).strip()
        if s:
            strings.append(s)
    return strings


def fix_cip(conn):
    """Parse CIP codes with embedded separators."""
    print("\n=== Fixing CIP codes ===")
    bcp_path = os.path.join(BACPAC_DATA, "dbo.cip", "TableData-000-00000.BCP")
    strings = read_utf16_strings(bcp_path)

    cur = conn.cursor()
    cur.execute("DELETE FROM cip_codes")

    inserted = 0
    for s in strings:
        # Pattern: 6-digit code (like "010101") followed by a separator char then title
        # e.g. "010101\Agricultural Business and Management, General."
        # or   "0100*Agriculture, General."
        m = re.match(r'^(\d{4,6})\s*[*\\>JFVL@~#$!^&]+\s*(.+)', s)
        if m:
            raw_code = m.group(1)
            title = m.group(2).strip().rstrip('.')

            # Format as XX.XXXX
            if len(raw_code) == 6:
                code = raw_code[:2] + '.' + raw_code[2:]
            elif len(raw_code) == 4:
                code = raw_code[:2] + '.' + raw_code[2:] + '00'
            else:
                code = raw_code

            if title and len(title) > 2:
                try:
                    cur.execute(
                        "INSERT INTO cip_codes (code, title) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                        (code, title[:500])
                    )
                    inserted += 1
                except:
                    conn.rollback()

    # Also handle the top-level 2-digit codes we found before
    for i, s in enumerate(strings):
        if re.match(r'^\d{2}$', s) and i + 1 < len(strings):
            code = s.zfill(2)
            title = strings[i + 1].strip().rstrip('.')
            if title and len(title) > 3 and not re.match(r'^\d', title):
                try:
                    cur.execute(
                        "INSERT INTO cip_codes (code, title) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                        (code, title[:500])
                    )
                    inserted += 1
                except:
                    conn.rollback()

    conn.commit()
    cur.execute("SELECT count(*) FROM cip_codes")
    total = cur.fetchone()[0]
    print(f"  Inserted: {inserted} -> Total in DB: {total}")

    cur.execute("SELECT code, title FROM cip_codes ORDER BY code LIMIT 10")
    for code, title in cur.fetchall():
        print(f"    {code}: {title[:80]}")


def fix_soc(conn):
    """Parse SOC codes where code+title are concatenated."""
    print("\n=== Fixing SOC codes ===")

    soc_tables = [
        ("dbo.socc", "current"),
        ("dbo.socc_2010", "2010"),
        ("dbo.socc_2018", "2018"),
    ]

    cur = conn.cursor()
    cur.execute("DELETE FROM soc_codes")
    total = 0

    for table_name, version in soc_tables:
        bcp_path = os.path.join(BACPAC_DATA, table_name, "TableData-000-00000.BCP")
        if not os.path.exists(bcp_path):
            continue

        strings = read_utf16_strings(bcp_path)
        inserted = 0

        for s in strings:
            # Pattern: 6-digit SOC code (like "111011") then separator char then title
            # e.g. "111011 Chief Executives"
            # or   "111021>General and Operations Managers"
            m = re.match(r'^(\d{6})\s*[A-Z>\\*@~#$!^&JFVL]?\s*(.+)', s)
            if m:
                raw_code = m.group(1)
                title = m.group(2).strip()

                # Format as XX-XXXX
                code = raw_code[:2] + '-' + raw_code[2:]

                if title and len(title) > 2:
                    try:
                        cur.execute(
                            "INSERT INTO soc_codes (code, title, version) VALUES (%s, %s, %s)",
                            (code, title[:500], version)
                        )
                        inserted += 1
                    except:
                        conn.rollback()

            # Also try: 7-digit with decimal like "5370646"
            m2 = re.match(r'^(\d{7})\s*(.+)', s)
            if m2 and not m:
                raw = m2.group(1)
                title = m2.group(2).strip()
                # Could be SOC + extra digit — try XX-XXXX format
                code = raw[:2] + '-' + raw[2:6]
                if title and len(title) > 2:
                    try:
                        cur.execute(
                            "INSERT INTO soc_codes (code, title, version) VALUES (%s, %s, %s)",
                            (code, title[:500], version)
                        )
                        inserted += 1
                    except:
                        conn.rollback()

        conn.commit()
        total += inserted
        print(f"  {table_name} ({version}): {inserted}")

    print(f"  Total SOC codes: {total}")
    cur.execute("SELECT code, title, version FROM soc_codes ORDER BY version, code LIMIT 10")
    for code, title, ver in cur.fetchall():
        print(f"    [{ver}] {code}: {title[:80]}")


def main():
    conn = psycopg2.connect(**PG_CONFIG)
    try:
        fix_cip(conn)
        fix_soc(conn)
    finally:
        conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
