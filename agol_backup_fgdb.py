import warnings
import logging
import os, sys, shutil, json, zipfile, re, time, datetime as dt
from urllib3.exceptions import InsecureRequestWarning
from joblib import Parallel, delayed, parallel_backend
from delete_fgdb_agol import *

from arcgis.gis import GIS
import urllib3
# =========================================================
# CONFIGURATION
# =========================================================
warnings.simplefilter("ignore", InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import os
from dotenv import load_dotenv

# --- Always resolve the .env relative to the script's own location ---
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")

if not os.path.exists(env_path):
    raise FileNotFoundError(f"❌ .env file not found at {env_path}")

# Load it explicitly
load_dotenv(dotenv_path=env_path, override=True)




LOG_FILE = "agol_backup.log"
logging.basicConfig(
    filename=LOG_FILE,
    filemode="w",   # ✅ overwrite instead of append
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(console)

# Folders
LOCAL_TEMP_FOLDER = r"E:\AGOL_BACKUP_15DAYS"  # <— faster SSD temp workspace
os.makedirs(LOCAL_TEMP_FOLDER, exist_ok=True)


# =========================================================
# HELPERS
# =========================================================
def safe_filename(name):
    """Clean ArcGIS item titles for safe Windows file/folder naming."""
    name = re.sub(r'[<>:"/\\|?*()\'’]', "_", name)
    name = re.sub(r'\s+', "_", name.strip())
    return name[:80]


def create_daily_folder(base_folder):
    folder_name = dt.datetime.now().strftime("%d_%b_%Y")
    folder_path = os.path.join(base_folder, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def cleanup_old_folders(base_folder, days=15):
    cutoff = dt.datetime.now() - dt.timedelta(days=days)
    if not os.path.exists(base_folder):
        return
    for f in os.listdir(base_folder):
        path = os.path.join(base_folder, f)
        if os.path.isdir(path):
            try:
                if dt.datetime.fromtimestamp(os.path.getmtime(path)) < cutoff:
                    shutil.rmtree(path)
                    logging.info(f"🗑️ Deleted old folder: {path}")
            except Exception as e:
                logging.warning(f"⚠️ Could not delete {path}: {e}")

# =========================================================
# EXPORT FEATURE SERVICE
# =========================================================
def export_feature_service(fs_id, fs_title, temp_folder, version, gis):
    """Export one hosted layer, download to temp, skip if already exists."""
    start = dt.datetime.now()
    safe_title = safe_filename(fs_title)
    backup_filename = f"{safe_title}_Backup_{version}"

    expected_zip_1 = os.path.join(temp_folder, backup_filename + ".zip")
    expected_zip_2 = os.path.join(temp_folder, backup_filename + ".gdb.zip")
    expected_folder = os.path.join(temp_folder, backup_filename)

    # =========================================================
    # 1️⃣ Skip if the ZIP already exists
    # =========================================================
    if os.path.exists(expected_zip_1) or os.path.exists(expected_zip_2):
        logging.info(f"⏭️ Skipping (already backed up): {fs_title}")
        return f"Skipped: {fs_title}"

    # =========================================================
    # 2️⃣ If a leftover folder exists from a previous crash → delete it
    # =========================================================
    if os.path.isdir(expected_folder):
        logging.warning(f"⚠️ Removing incomplete leftover folder: {expected_folder}")
        try:
            shutil.rmtree(expected_folder)
        except Exception as e:
            logging.error(f"❌ Could not remove leftover folder {expected_folder}: {e}")

    try:
        feature_service = gis.content.get(fs_id)
        if not feature_service:
            raise ValueError("Item not found")

        logging.info(f"🚀 Exporting: {fs_title}")

        # Export to AGOL
        export_item = feature_service.export(
            title=backup_filename,
            export_format="File Geodatabase"
        )

        # Download
        fgdb_path = export_item.download(save_path=temp_folder)

        # Handle AGOL returning folder instead of zip
        final_zip_path = fgdb_path
        if not final_zip_path.lower().endswith(".zip"):
            # Compress folder manually
            final_zip_path = fgdb_path + ".zip"
            with zipfile.ZipFile(final_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(fgdb_path):
                    for f in files:
                        full = os.path.join(root, f)
                        arc = os.path.relpath(full, os.path.dirname(fgdb_path))
                        zipf.write(full, arc)

            shutil.rmtree(fgdb_path)

        end = dt.datetime.now()
        logging.info(
            f"✅ Exported {fs_title} → {final_zip_path} "
            f"({(end-start).total_seconds():.1f}s)"
        )

        return f"Exported: {fs_title}"

    except Exception as e:
        logging.error(f"❌ Error exporting {fs_title}: {e}")
        return None


# =========================================================
# MAIN BACKUP
# =========================================================
def export_all_hosted_layers(gis):
    version = dt.datetime.now().strftime("%d_%b_%Y")
    temp_folder = create_daily_folder(LOCAL_TEMP_FOLDER)

    logging.info(f"📁 Temp folder: {temp_folder}")

    items = gis.content.search(
        query=f"owner:{gis.users.me.username} AND type:'Feature Service'",
        max_items=700
    )
    logging.info(f"Found {len(items)} hosted feature layers.")

    if not items:
        logging.info("⚠️ No hosted feature layers found. Exiting.")
        return

    max_threads = min(8, max(2, os.cpu_count() // 2))
    logging.info(f"🚀 Starting export for {len(items)} layers using {max_threads} threads...")

    start_all = dt.datetime.now()

    with parallel_backend("threading", n_jobs=max_threads):
        results = Parallel(verbose=5)(
            delayed(export_feature_service)(item.id, item.title, temp_folder, version, gis)
            for item in items
        )

    end_all = dt.datetime.now()
    duration = end_all - start_all

    exported = sum(1 for r in results if r and r.startswith("Exported"))
    skipped = sum(1 for r in results if r and r.startswith("Skipped"))
    logging.info(f"📊 Summary → Total: {len(items)}, Exported: {exported}, Skipped(existing): {skipped}")
    logging.info(f"⏱️ Total Runtime: {duration}")

    print(f"\n✅ Backup Completed. Duration: {duration}")

    logging.info("🔍 Validating final backup count...")
    file_count = len([f for f in os.listdir(temp_folder) if f.lower().endswith(".zip")])
    logging.info(f"📦 Total ZIP files in backup folder: {file_count}")

# =========================================================
# MAIN EXECUTION
# =========================================================
if __name__ == "__main__":
    try:
        start_run = dt.datetime.now()
        logging.info("🔐 Authenticating with ArcGIS Online...")
        gis = GIS(
        os.getenv("PORTAL_URL"),
        os.getenv("USERNAME"),
        os.getenv("PASSWORD"),
        verify_cert=False
    )

        logging.info(f"✅ Logged in as {gis.users.me.username}")

        cleanup_old_folders(LOCAL_TEMP_FOLDER, days=15)



        export_all_hosted_layers(gis)
        end_run = dt.datetime.now()
        logging.info(f"✅ AGOL Daily Backup Completed | Duration: {end_run - start_run}")
        result = cleanup_exported_fgdbs(
                env_file=".env",
                log_file="agol_fgdb_cleanup.log",
                max_items=2000,
                verify_cert=False
            )

        print("FGDB Cleanup Result:", result)

    except Exception as e:
        logging.critical(f"🔥 Critical failure: {e}")
