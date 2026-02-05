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

### El truc "DPx" (Corrupció intencionada)
En lloc d'intentar endevinar la contrasenya, corrompem la clau perquè l'Excel s'espanti i ens deixi entrar.

**Passos:**
1.  **Accedir al codi binari:**
    *   **En .xls:** Obre el fitxer directament amb Editor Hexadecimal.
    *   **En .xlsm:** Canvia a `.zip`, extreu `xl/vbaProject.bin` i obre aquest fitxer amb Editor Hexadecimal.
2.  **Buscar la clau:** Busca el text `DPB=` (pot ser que necessitis buscar en mode text/ANSI).
3.  **El Hack:** Canvia la `B` per una `x`.
    *   Original: `DPB="...claus..."`
    *   Modificat: `DPx="...claus..."`
    *   *Nota:* Has de mantenir el mateix número de bytes, només canvia la lletra.
4.  **Reconstruir:**
    *   Guarda el canvi. (Si era .xlsm, torna a posar el `vbaProject.bin` al ZIP).
5.  **Obrir a Excel:**
    *   Obre el fitxer. Et donarà errors com "Clau no vàlida" (Invalid Key) o "Projecte corrupte". **Accepta'ls tots (Sí/Yes).**
6.  **Fixar-ho definitivament:**
    *   Ves a l'editor VBA (Alt+F11).
    *   Apareixerà un error "Error no esperat" (Unexpected Error). Accepta.
    *   Ves a **Eines (Tools)** > **Propietats de VBAProject**.
    *   Ves a la pestanya **Protecció**.
    *   Escriu una **NOVA** contrasenya (la que vulguis) i guarda el fitxer.
    *   Ara ja tens el control total amb la teva contrasenya.
