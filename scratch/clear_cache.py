import os
import sys

from backend.database import SessionLocal
from backend.models import ScrapeCache

def clear_cache():
    db = SessionLocal()
    count = db.query(ScrapeCache).count()
    db.query(ScrapeCache).delete()
    db.commit()
    print(f"Cleared {count} items from ScrapeCache!")

if __name__ == "__main__":
    clear_cache()
