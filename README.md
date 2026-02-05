# Excel Sheet Unlocker

A lightweight tool to remove worksheet and workbook protection from legacy Excel 97-2003 (.xls) files without knowing the password. This utility modifies the binary structure of the file to disable protection flags.

## Quick Start

1. Place `unlocker.py` in the same directory as your protected `.xls` files.
2. Run the script:
   ```bash
   python unlocker.py
   ```
3. The script will process all `.xls` files in the directory and generate unlocked versions with the `_unlocked.xls` suffix.
4. Open the new files in Excel—protection will be disabled without requiring a password.

## How It Works

Excel 97-2003 files use the BIFF8 binary format. Worksheet and workbook protection is controlled by a simple 2-byte flag within the `PROTECT` record (`0x0012`):

- Protected state: `12 00 02 00 01 00`
- Unprotected state: `12 00 02 00 00 00`

The script performs a binary replacement of all occurrences of the protected pattern with the unprotected version. This disables protection at the file level—Excel will no longer enforce restrictions when the modified file is opened.

## Alternative Methods for Other Scenarios

### Modern Excel Files (.xlsx / .xlsm)

Files created with Excel 2007 and later use the Office Open XML format (a ZIP archive containing XML files). To remove worksheet protection:

1. Rename the file extension from `.xlsx` to `.zip`.
2. Extract the archive and navigate to `xl/worksheets/`.
3. Open the relevant `sheetN.xml` file in a text editor.
4. Locate and delete the `<sheetProtection ... />` tag.
5. Save the file, repackage the ZIP archive, and rename the extension back to `.xlsx`.

To remove workbook structure protection, edit `xl/workbook.xml` and remove the `<workbookProtection ... />` tag.

### VBA Project Password Removal

To bypass VBA project password protection (applies to both `.xls` and `.xlsm` files):

1. For `.xls`: Open the file directly in a hex editor.  
   For `.xlsm`: Rename to `.zip`, extract `xl/vbaProject.bin`, and open it in a hex editor.
2. Search for the ASCII string `DPB=`.
3. Change the `B` to `x` (`DPB=` → `DPx=`), preserving byte length.
4. Save the file and restore the original container if needed.
5. Open in Excel—accept any corruption warnings.
6. In the VBA editor (Alt+F11), go to Tools → VBAProject Properties → Protection, set a new password, and save the workbook.

## Limitations

This tool **does not**:
- Remove file-open passwords (encryption).
- Recover or crack forgotten passwords.
- Modify VBA project protection.
- Work on modern `.xlsx` files (use the ZIP/XML method above instead).

## Disclaimer

Use this tool only on files you own or have explicit permission to modify. Bypassing protection mechanisms may violate terms of service or local laws in certain contexts. The author assumes no liability for misuse.
