"""
Safe vector migration and HNSW re-indexing script.
Migrates all existing study-material note_chunks in PostgreSQL to the unified
768-dimensional local vector space.
Preserves course IDs, material IDs, chunk text, titles, and access controls.
"""
import sys
import os
import logging

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database.postgres import SessionLocal
from app.services.embedding_service import reindex_all_database_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_embeddings")


def run_migration():
    logger.info("Initializing vector migration session...")
    db = SessionLocal()
    try:
        result = reindex_all_database_chunks(db)
        logger.info(f"Vector migration result: {result}")
        print("\n" + "="*60)
        print("VECTOR MIGRATION SUCCESSFUL")
        print(f"Total Chunks Processed: {result['total_chunks']}")
        print(f"Migrated Chunks:        {result['migrated_chunks']}")
        print(f"Vector Dimension:       {result['dimension']}")
        print(f"Embedding Provider:     {result['provider']}")
        print(f"HNSW Index Reindexed:   {result['hnsw_reindexed']}")
        print("="*60 + "\n")
        return result
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
