# Installing pgvector on Windows (PostgreSQL 18)

## Your Setup
- PostgreSQL 18.3, installed at `C:\Program Files\PostgreSQL\18\`
- Windows, no Visual Studio build tools confirmed

---

## Option 1: Pre-built Binary (Fastest)

pgvector publishes Windows builds for each PostgreSQL version.

### Steps:

1. **Download the pgvector Windows release** for PG 18:
   - Go to: https://github.com/pgvector/pgvector/releases
   - Download `pgvector-X.X.X-pg18-windows-x64.zip`
   - If no PG 18 build exists yet, use Option 2 or 3

2. **Extract and copy files:**
   ```powershell
   # Extract the zip, then copy:
   Copy-Item vector.dll "C:\Program Files\PostgreSQL\18\lib\"
   Copy-Item vector.control "C:\Program Files\PostgreSQL\18\share\extension\"
   Copy-Item vector--*.sql "C:\Program Files\PostgreSQL\18\share\extension\"
   ```

3. **Restart PostgreSQL:**
   ```powershell
   Restart-Service postgresql-x64-18
   ```

4. **Enable the extension:**
   ```sql
   CREATE EXTENSION vector;
   ```

5. **Convert skill embeddings:**
   ```sql
   -- Add vector column
   ALTER TABLE skills ADD COLUMN embedding_vector vector(1536);

   -- Convert JSON text embeddings to vector format
   UPDATE skills
   SET embedding_vector = embedding::vector
   WHERE embedding IS NOT NULL;

   -- Create index for similarity search
   CREATE INDEX ON skills USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 50);
   ```

---

## Option 2: Build from Source (if no binary available)

### Prerequisites:
```powershell
# Install Visual Studio Build Tools
winget install Microsoft.VisualStudio.2022.BuildTools

# In Visual Studio Installer, select:
# - "Desktop development with C++"
# - Windows SDK
```

### Build:
```powershell
# Clone pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector

# Open "x64 Native Tools Command Prompt for VS 2022"
# Set PostgreSQL paths
set "PGROOT=C:\Program Files\PostgreSQL\18"
set "PATH=%PGROOT%\bin;%PATH%"

# Build and install
nmake /F Makefile.win
nmake /F Makefile.win install
```

Then restart PostgreSQL and run `CREATE EXTENSION vector;`

---

## Option 3: Use Docker (No Install Needed)

If building is problematic, run a pgvector-enabled PostgreSQL in Docker:

```powershell
docker run -d --name wfdos-pg \
  -e POSTGRES_PASSWORD=wfdos2026 \
  -e POSTGRES_DB=wfd_os \
  -p 5433:5432 \
  pgvector/pgvector:pg17

# Connect on port 5433 instead of 5432
# Then restore the wfd_os data from a pg_dump
```

---

## After Installation: Verify

```sql
-- Check extension is loaded
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Test vector operations
SELECT '[1,2,3]'::vector <=> '[4,5,6]'::vector AS cosine_distance;

-- Verify skill embeddings converted
SELECT skill_name, embedding_vector IS NOT NULL as has_vector
FROM skills LIMIT 5;
```

---

## What This Enables

With pgvector installed, the Matching Agent can:
- Store student profile embeddings as `vector(1536)`
- Store job listing embeddings as `vector(1536)`
- Run cosine similarity search: `ORDER BY embedding <=> query_vector`
- Use IVFFlat or HNSW indexes for fast approximate nearest neighbor search
- All within PostgreSQL — no external vector database needed
