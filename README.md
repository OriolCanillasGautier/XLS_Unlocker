# Excel 97-2003 Unlocker & Forensics Toolkit

Technical toolkit for analyzing and bypassing protection mechanisms in legacy Excel 97-2003 BIFF8/OLE files.

Focus areas:
*   BIFF8 worksheet protection records (0x0012 / 0x0013).
*   OLE/VBA PROJECT stream metadata (CMG/DPB/GC tags).
*   Deterministic byte-level transforms suitable for repeatable forensics.

## Contents

### 1. `excel_unlocker.py` (Protection Removal)
Main script to disable worksheet and VBA project protection in-place for target files.
*   **Worksheets:** Rewrites BIFF8 PROTECT records (0x0012) to clear the protection flag.
*   **VBA:** Voids the CMG/DPB/GC tags in the PROJECT stream while preserving byte alignment.
*   **Output:** Writes a new file ending in `_unlocked.xls`.

Notes:
*   The PROTECT flag is a gate: once cleared, Excel does not validate the 16‑bit hash.
*   Tag-voiding is non-destructive at the stream level (lengths preserved), which avoids load-time corruption.

### 2. `password_cracker.py` (Password Recovery)
Recovers worksheet passwords by matching BIFF8 PASSWORD records to candidate hashes.
*   Scans raw BIFF8 data for PASSWORD records (0x0013, length 2).
*   Evaluates 5 known hash variants (standard, 15-bit, reverse, positional, MSDN).
*   Supports custom wordlists, directory-based wordlists, optional word extraction, and configurable brute-force bounds.
*   Usage: `python password_cracker.py <file.xls>`

Supported inputs:
*   One or more wordlist files.
*   A directory of `.txt` wordlists.
*   Optional extraction of ASCII-like tokens from the file.

Wordlist usage examples:
*   Single wordlist file:
	```bash
	python password_cracker.py target.xls --wordlist wordlist.txt
	```
*   Multiple wordlist files:
	```bash
	python password_cracker.py target.xls --wordlist list1.txt --wordlist list2.txt
	```
*   Directory of wordlists (all `.txt` files are loaded):
	```bash
	python password_cracker.py target.xls --wordlist-dir wordlists
	```
*   Combine directory + extraction + extended brute force:
	```bash
	python password_cracker.py target.xls --wordlist-dir wordlists --extract-words --max-len 6
	```

### 3. `vba_hash_extractor.py` (Forensics)
Extracts VBA project protection metadata in a format suitable for offline cracking tools.
*   Usage: `python vba_hash_extractor.py <file.xls> > hash.txt`

---

## Execution Notes

The scripts operate directly on BIFF8/OLE structures and make deterministic, byte-level modifications or comparisons. Use in a controlled environment and keep originals intact.

Example workflows:

*   **Disable protections (batch):**
	```bash
	python excel_unlocker.py
	```

*   **Recover worksheet passwords with defaults:**
	```bash
	python password_cracker.py target.xls
	```

*   **Use external wordlists + extract tokens + extend brute force:**
	```bash
	python password_cracker.py target.xls --wordlist wordlist.txt --wordlist-dir wordlists --extract-words --max-len 5
	```

*   **Generate a VBA hash for offline cracking:**
	```bash
	python vba_hash_extractor.py target.xls > hash.txt
	```

---

## How it Works

### Worksheet Protection (Bit-Flip)
Worksheet protection is encoded as BIFF8 record 0x0012 (PROTECT). Clearing the flag disables the protection gate and bypasses hash verification.

Internally, the tool scans for the 0x0012 record header and clears the 2‑byte value field, keeping record length and surrounding bytes intact.

### VBA Protection (Tag Voiding)
VBA project protection metadata is stored as hex-encoded tags in the PROJECT stream. Replacing these values with same-length padding neutralizes the protection while preserving stream layout.

The PROJECT stream remains valid because only the tag payloads are replaced; tag names, delimiters, and lengths are unchanged.

### Password Hash (16-bit)
The legacy worksheet password hash is 16-bit, making collisions unavoidable. Different passwords can satisfy the same hash. The cracker evaluates multiple algorithm variants to cover version differences.

This is why results are a candidate set, not a single ground-truth string. The intended validation is at the application level.

---

## Technical Notes

*   Scope: `.xls` only (Excel 97-2003, BIFF8/OLE).
*   Output files are created with `_unlocked.xls` suffix to preserve originals.
*   Requirements: Python 3.x (no external dependencies).
