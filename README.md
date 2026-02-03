Below is a complete **GitHub README.md** that’s **divided into 2 parts**: **(1) Backup AGOL Hosted Feature Layers to FGDB** and **(2) Delete/cleanup exported FGDB items from AGOL**. It matches what your scripts do, including `.env` loading, logging, local folder retention, and the FGDB cleanup function.  

---

````md
# AGOL Hosted Feature Layer Backup + FGDB Cleanup (Python)

Automate **daily backups** of ArcGIS Online (AGOL) **Hosted Feature Layers** to **File Geodatabase exports** (downloaded locally as `.zip`), and optionally **cleanup/delete exported File Geodatabase items** from AGOL to avoid storage clutter.

This repo contains two scripts:
1) **Backup**: Export & download Hosted Feature Layers as FGDB ZIPs  
2) **Cleanup**: Delete **File Geodatabase** items from AGOL content (exports)

---

## ✨ Features

### ✅ Part 1 — Backup Hosted Feature Layers (FGDB Export)
- Logs into AGOL using `.env`
- Searches all **Feature Service** items owned by the authenticated user
- Exports each service to **File Geodatabase**
- Downloads FGDB export locally (`.zip` or `.gdb.zip`)
- Skips already-backed-up exports if ZIP already exists
- Uses **parallel processing** for faster exports
- Keeps a **daily folder** structure and deletes local backups older than N days (default 15)
- Writes logs to `agol_backup.log`

### 🧹 Part 2 — Cleanup/Delete Exported FGDB Items in AGOL
- Logs into AGOL using `.env`
- Searches items of type **File Geodatabase**
- Permanently deletes them (`permanent=True`)
- Writes logs to `agol_fgdb_cleanup.log`
- Returns a summary dictionary: `{"deleted": X, "failed": Y}`

---

## 📁 Repo Structure

```text
.
├── agol_backup_fgdb.py          # Part 1: Backup/export + (optional) calls cleanup
├── delete_fgdb_agol.py          # Part 2: Cleanup FGDB items in AGOL
├── .env                         # Credentials (NOT committed)
├── agol_backup.log              # Backup logs (generated)
└── agol_fgdb_cleanup.log        # Cleanup logs (generated)
````

---

## 🔧 Requirements

* Python 3.9+ recommended
* ArcGIS API for Python
* dotenv
* joblib
* urllib3

Install dependencies:

```bash
pip install arcgis python-dotenv joblib urllib3
```

---

## 🔐 Environment Setup (.env)

Create a `.env` file in the **same folder as the scripts**:

```env
PORTAL_URL=https://www.arcgis.com
USERNAME=your_username
PASSWORD=your_password
```

> ✅ The scripts explicitly resolve `.env` relative to the script location.

---

# PART 1 — Backup Hosted Feature Layers to FGDB (Local ZIP)

## ▶️ How it works

The backup script:

* Creates a daily folder like: `E:\AGOL_BACKUP_15DAYS\02_Feb_2026\`
* Exports each Hosted Feature Layer (Feature Service) to File Geodatabase
* Downloads the export to the daily folder
* Skips exports if the ZIP already exists
* Cleans local folders older than 15 days

## ⚙️ Configure Local Backup Folder

Inside `agol_backup_fgdb.py`, update:

```python
LOCAL_TEMP_FOLDER = r"E:\AGOL_BACKUP_15DAYS"
```

## 🚀 Run Backup

```bash
python agol_backup_fgdb.py
```

## 🧾 Output & Logs

* Local ZIPs stored under `LOCAL_TEMP_FOLDER\DD_Mon_YYYY\`
* Logs written to: `agol_backup.log`

Example log events:

* `🚀 Exporting: <Layer Name>`
* `✅ Exported <Layer Name> → <path to zip>`
* `⏭️ Skipping (already backed up): <Layer Name>`
* `🗑️ Deleted old folder: <older daily folder>`

---

# PART 2 — Delete/Cleanup FGDB Exports from AGOL

## ✅ What it deletes

This cleanup removes items of type:

* **File Geodatabase**

Query used:

* `owner:<username> AND type:'File Geodatabase'`

This is useful because AGOL exports can accumulate quickly and consume content/storage.

## ▶️ Run Cleanup (Standalone)

You can run cleanup by importing and calling the function:

```python
from delete_fgdb_agol import cleanup_exported_fgdbs

result = cleanup_exported_fgdbs(
    env_file=".env",
    log_file="agol_fgdb_cleanup.log",
    max_items=2000,
    verify_cert=False
)

print(result)  # {"deleted": X, "failed": Y}
```

## 🧾 Cleanup Logs

* Logs written to: `agol_fgdb_cleanup.log`
* Example messages:

  * `🧹 Found <n> File Geodatabases. Deleting...`
  * `🗑️ Deleted: <title> (<itemid>)`
  * `⚠️ Could not delete <title>: <error>`

---

## 🔁 Combined Flow (Backup + Cleanup)

Your `agol_backup_fgdb.py` already calls cleanup at the end (after exports), so running:

```bash
python agol_backup_fgdb.py
```

can do:

1. Daily FGDB backups (download locally)
2. Cleanup FGDB exports from AGOL content

---

## 🧩 Architecture (High Level)

```text
AGOL Hosted Feature Layers (Feature Service)
        |
        |  Export (File Geodatabase)
        v
AGOL Export Item (File Geodatabase)
        |
        |  Download ZIP
        v
Local Daily Folder (E:\AGOL_BACKUP_15DAYS\DD_Mon_YYYY\*.zip)
        |
        |  Optional Cleanup
        v
Delete AGOL "File Geodatabase" Items (exports only)
```

---

## 🧪 Suggested “Sample Screenshots” Section (Optional)

Add screenshots like:

* `agol_backup.log` successful run
* Local folder showing ZIP outputs
* `agol_fgdb_cleanup.log` showing delete summary

Recommended folder:

```text
screenshots/
  backup_log.png
  backup_folder.png
  cleanup_log.png
```

Then embed:

```md
![Backup Log](screenshots/backup_log.png)
```

---

## 🏷 Suggested Repo Description + Topics

**Repo description (GitHub):**

> Daily backup of ArcGIS Online Hosted Feature Layers to FGDB ZIPs with optional cleanup of exported FGDB items.

**Topics:**

* `arcgis`
* `arcgis-online`
* `agol`
* `gis`
* `python`
* `data-backup`
* `file-geodatabase`
* `automation`
* `joblib`
* `etl`

---

## ⚠️ Notes / Safety

* Cleanup uses `permanent=True` → deletes FGDB items permanently from your AGOL content.
* It only targets **File Geodatabase** items, not Feature Services.
* Keep your `.env` out of git:

  * Add to `.gitignore`:

    ```text
    .env
    *.log
    ```

---

