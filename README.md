# Excel 97-2003 Unlocker & Forensics Toolkit

Technical toolkit for analyzing and bypassing protection mechanisms in legacy Excel 97-2003 BIFF8/OLE files.

## Contents

### 1. `excel_unlocker.py` (Protection Removal)
Main script to disable worksheet and VBA project protection in-place for target files.
*   **Worksheets:** Rewrites BIFF8 PROTECT records (0x0012) to clear the protection flag.
*   **VBA:** Voids the CMG/DPB/GC tags in the PROJECT stream while preserving byte alignment.
*   **Output:** Writes a new file ending in `_unlocked.xls`.

### 2. `password_cracker.py` (Password Recovery)
Recovers worksheet passwords by matching BIFF8 PASSWORD records to candidate hashes.
*   Scans raw BIFF8 data for PASSWORD records (0x0013, length 2).
*   Evaluates 5 known hash variants (standard, 15-bit, reverse, positional, MSDN).
*   Supports custom wordlists, directory-based wordlists, optional word extraction, and configurable brute-force bounds.
*   Usage: `python password_cracker.py <file.xls>`

### 3. `vba_hash_extractor.py` (Forensics)
Extracts VBA project protection metadata in a format suitable for offline cracking tools.
*   Usage: `python vba_hash_extractor.py <file.xls> > hash.txt`

---

## Execution Notes

The scripts operate directly on BIFF8/OLE structures and make deterministic, byte-level modifications or comparisons. Use in a controlled environment and keep originals intact.

---

## How it Works

### Worksheet Protection (Bit-Flip)
Worksheet protection is encoded as BIFF8 record 0x0012 (PROTECT). Clearing the flag disables the protection gate and bypasses hash verification.

### VBA Protection (Tag Voiding)
VBA project protection metadata is stored as hex-encoded tags in the PROJECT stream. Replacing these values with same-length padding neutralizes the protection while preserving stream layout.

### Password Hash (16-bit)
The legacy worksheet password hash is 16-bit, making collisions unavoidable. Different passwords can satisfy the same hash. The cracker evaluates multiple algorithm variants to cover version differences.

---

## Technical Notes

*   Scope: `.xls` only (Excel 97-2003, BIFF8/OLE).
*   Output files are created with `_unlocked.xls` suffix to preserve originals.
*   Requirements: Python 3.x (no external dependencies).
