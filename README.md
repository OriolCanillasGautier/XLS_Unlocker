# Excel 97-2003 Unlocker & Forensics Toolkit

Professional toolkit to unlock legacy Excel files (.xls) and VBA projects.

## Contents

### 1. `excel_unlocker.py` (Automatic Unlocker)
Main script. Removes all protections from any .xls file in the current folder.
*   **Worksheets:** Flips the BIFF8 PROTECT record bit from 1 (protected) to 0 (unprotected).
*   **Macros (VBA):** Voids the security configuration tags (CMG, DPB, GC) by overwriting them with spaces, making Excel load the project as unprotected.
*   **Output:** Creates a new file ending in `_unlocked.xls`.

### 2. `password_cracker.py` (Password Recovery)
Attempts to recover the actual plaintext password from an .xls file.
*   Scans the binary for PASSWORD records and extracts the 16-bit hashes.
*   Tests 5 different hash algorithm variants (standard, 15-bit, reverse, positional, MSDN).
*   Runs a dictionary attack followed by a short brute force.
*   Prints a summary of all candidate passwords at the end.
*   Usage: `python password_cracker.py <file.xls>`

### 3. `vba_hash_extractor.py` (Forensics)
Extracts the VBA project password hash in a format compatible with John the Ripper for offline cracking.
*   Usage: `python vba_hash_extractor.py <file.xls> > hash.txt`
*   Then crack with: `john hash.txt`

---

## Quick Start

**To remove all protections (sheets + macros):**
1.  Copy your locked `.xls` files into this folder.
2.  Run:
    ```bash
    python excel_unlocker.py
    ```
3.  Open the new `_unlocked.xls` files.

**To recover the actual password:**
```bash
python password_cracker.py your_file.xls
```

---

## How it Works

### Worksheet Protection (Bit-Flip)
Excel 97-2003 stores sheet protection as a BIFF8 binary record:
```
12 00 02 00 01 00
 |     |     |
 |     |     Value: 01 = Protected, 00 = Unprotected
 |     Length: 2 bytes
 Record type: 0x0012 (PROTECT)
```
The tool simply changes `01 00` to `00 00`. Since the password hash is only checked when protection is active, Excel never asks for it.

### VBA Protection (Tag Voiding)
VBA project passwords are stored as hex-encoded tags inside the OLE stream.
The tool overwrites these tags with spaces (0x20), preserving byte alignment. Excel then loads the project as if it never had a password, without triggering corruption errors.

### Password Hash (16-bit)
The legacy hash is only 16 bits wide (65536 possible values), so collisions are inevitable. Multiple passwords will produce the same hash, and any collision is accepted by Excel. The cracker tests 5 different algorithm variants because Microsoft's implementation changed slightly across versions.

---

## Technical Notes

*   These tools only work with `.xls` files (Excel 97-2003, BIFF8/OLE format).
*   **Modern Excel (.xlsx/.xlsm):** Rename to `.zip`, navigate to `xl/worksheets/`, and delete the `<sheetProtection ... />` XML tag from each sheet.
*   **Requirements:** Python 3.x (no external dependencies).
