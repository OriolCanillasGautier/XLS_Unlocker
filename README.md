# Excel 97-2003 Unlocker & Forensics Toolkit

Professional toolkit to unlock legacy Excel files (.xls) and VBA projects.

## Contents

### 1. `excel_unlocker.py` (Automatic Tool)
This is the main script.
*   **What it does:** Takes any .xls file in the folder and removes all protections.
*   **How it works:**
    *   **Worksheets:** Changes the protection bit (1 -> 0).
    *   **Macros (VBA):** Completely removes security configuration tags (CMG, DPB, GC) by replacing them with empty spaces ("Voiding").
*   **Result:** Excel opens without asking for a password and allows viewing/editing VBA code without errors.

### 2. `password_recovery.py` (Password Recovery)
Use this if you need to know "what the password was" for Worksheets (not for macros).
*   Includes a list of known collisions for the 0xca35 hash (the most common one).
*   Examples: anime, flag1, data!.

### 3. `vba_hash_extractor.py` (Forensics)
Use this if you need to recover the original VBA project password (via real brute force) instead of simply deleting it.
*   Extracts the file "hash" in a format compatible with John the Ripper.
*   Usage: `python vba_hash_extractor.py file.xls > hash.txt`

---

## How to use

1.  Copy your locked .xls files into this folder.
2.  Open a terminal (PowerShell or CMD).
3.  Run:
    ```bash
    python excel_unlocker.py
    ```
4.  New files ending in `_unlocked.xls` will be created.

---

## Technical Notes

*   These tools work by modifying the binary bits of the OLE Compound Document format (BIFF8).
*   **Modern Excel (.xlsx/.xlsm):** These scripts DO NOT work for new files (XML). For those, change the extension to .zip and edit the internal XMLs.
