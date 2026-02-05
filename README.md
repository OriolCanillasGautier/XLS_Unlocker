# Guia Completa Mestra: Desbloqueig d'Excel

Aquesta guia cobreix les tècniques per eliminar contrasenyes de protecció de fulls, estructura de llibres i projectes VBA (Macros), tant per als formats antics com per als moderns.

---

## 🟢 PART 1: Excel Modern (.xlsx / .xlsm)
Els fitxers moderns (Excel 2007 en endavant) són en realitat fitxers **ZIP** plens d'XML. Això fa que siguin molt fàcils de modificar sense editors hexadecimals complexos (excepte per a les macros).

### 1. Desbloquejar Fulls de Càlcul (Worksheets)
Si no pots editar cel·les en un full concret:

1.  **Canvia l'extensió** del fitxer: de `fitxer.xlsx` a `fitxer.zip`.
2.  Obre el ZIP (amb Windows o 7-Zip).
3.  Navega a la carpeta: `xl/worksheets/`.
4.  Veuràs fitxers com `sheet1.xml`, `sheet2.xml`, etc. Extreu el que vulguis desbloquejar.
5.  Obre l'XML amb el Bloc de Notes (o VS Code).
6.  Busca l'etiqueta que comença per `<sheetProtection ...`.
7.  **Esborra tota l'etiqueta** (des de `<` fins a `/>`).
    *   *Exemple:* Esborra `<sheetProtection algorithmName="SHA-512" hashValue="..." saltValue="..." ... />`
8.  Guarda el fitxer XML i torna'l a posar dins del ZIP, sobreescrivint l'antic.
9.  Torna a canviar l'extensió de `.zip` a `.xlsx`.

### 2. Desbloquejar l'Estructura del Llibre
Si no pots afegir, moure, amagar o esborrar fulls:

1.  Fes el mateix procés del ZIP.
2.  Navega a la carpeta `xl/`.
3.  Edita el fitxer `workbook.xml`.
4.  Busca i esborra l'etiqueta `<workbookProtection ... />`.

---

## 🟠 PART 2: Excel Antic (.xls) - Format Binari
Els fitxers antics (97-2003) no són ZIPs, sinó contenidors binaris OLE (Compound File Binary Format). Tot és un sol "blob" de dades.

### 1. Desbloquejar Fulls (El mètode "bit-flip")
La protecció és un simple interruptor binari.
*   **Eina necessària:** Editor Hexadecimal (HxD) o l'script de Python inclòs (`unlocker.py`).
*   **El procediment:**
    1.  Obre el fitxer `.xls` amb un editor Hexadecimal.
    2.  Busca la seqüència (**Hex**): `12 00 02 00 01 00`
        *   `12 00`: Registre "PROTECT"
        *   `02 00`: Longitud 2 bytes
        *   `01 00`: Valor 1 (Activat)
    3.  Substitueix-la per: `12 00 02 00 00 00`
    4.  Repeteix per cada vegada que apareguip (una per cada full protegit).
    5.  Guarda. L'Excel es pensarà que la protecció està desactivada.

---

## 🔴 PART 3: Desbloquejar Macros VBA (Tots els formats)
La protecció del projecte VBA (contrasenya per veure/editar codi) funciona gairebé igual en tots dos formats, perquè els fitxers `.xlsm` moderns guarden les macros dins d'un fitxer binari anomentat `vbaProject.bin` que té l'estructura antiga.

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
