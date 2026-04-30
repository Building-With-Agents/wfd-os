-- Enable pgvector in the wfdos database so the `skills.embedding_vector`
-- column (referenced from agents/market-intelligence/tools/semantic_skills.py
-- and agents/portal/college_api.py) can be added when the canonical schema
-- is defined.
CREATE EXTENSION IF NOT EXISTS vector;
