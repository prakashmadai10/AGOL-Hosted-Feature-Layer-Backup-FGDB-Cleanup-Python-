"""
agol_cleanup_fgdb.py
Deletes all File Geodatabase (.zip exports) from ArcGIS Online content.
Designed to be imported and called from main.py
"""

from arcgis.gis import GIS
import datetime as dt
import logging
import os
from dotenv import load_dotenv


def cleanup_exported_fgdbs(
    env_file: str = ".env",
    log_file: str = "agol_fgdb_cleanup.log",
    max_items: int = 2000,
    verify_cert: bool = False
):
    """
    Deletes all File Geodatabase items owned by the authenticated AGOL user.

    Parameters
    ----------
    env_file : str
        Path to .env file (relative or absolute)
    log_file : str
        Log file name
    max_items : int
        Max number of FGDB items to search
    verify_cert : bool
        SSL certificate verification flag
    """

    # --- Resolve .env path ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = env_file if os.path.isabs(env_file) else os.path.join(script_dir, env_file)

    if not os.path.exists(env_path):
        raise FileNotFoundError(f"❌ .env file not found at {env_path}")

    load_dotenv(dotenv_path=env_path, override=True)

    # --- Logging setup ---
    logging.basicConfig(
        filename=log_file,
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(console)

    # --- Connect to AGOL ---
    gis = GIS(
        os.getenv("PORTAL_URL"),
        os.getenv("USERNAME"),
        os.getenv("PASSWORD"),
        verify_cert=verify_cert
    )

    logging.info("🔐 Connecting to ArcGIS Online...")
    logging.info(f"✅ Logged in as {gis.users.me.username}")

    # --- Search FGDB exports ---
    logging.info("🔍 Searching for File Geodatabase exports...")
    items = gis.content.search(
        query=f"owner:{gis.users.me.username} AND type:'File Geodatabase'",
        max_items=max_items
    )

    if not items:
        logging.info("✅ No File Geodatabases found — nothing to delete.")
        return {"deleted": 0, "failed": 0}

    logging.info(f"🧹 Found {len(items)} File Geodatabases. Deleting...")

    deleted = 0
    failed = 0

    for item in items:
        try:
            item.delete(permanent=True)
            logging.info(f"🗑️ Deleted: {item.title} ({item.id})")
            deleted += 1
        except Exception as e:
            logging.warning(f"⚠️ Could not delete {item.title}: {e}")
            failed += 1

    logging.info(f"✅ Cleanup complete → Deleted: {deleted}, Failed: {failed}")
    logging.info(f"🕒 Finished at {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return {"deleted": deleted, "failed": failed}
