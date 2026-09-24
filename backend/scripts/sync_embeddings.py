"""
Wrapper script para ejecutar la sincronización de embeddings desde la CLI.
Uso:
  python backend/scripts/sync_embeddings.py [--limit 100] [--batch-size 50] [--force]
"""
import sys
import os
from pathlib import Path

# Añadir backend al sys.path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.jobs.sync_embeddings import main

if __name__ == "__main__":
    main()
