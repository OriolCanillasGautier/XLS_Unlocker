# Excel 97-2003 Unlocker & Forensics Toolkit

Set d'eines professional per desbloquejar fitxers Excel antics (`.xls`) i projectes VBA.

## 📂 Contingut

### 1. `excel_unlocker.py` (L'eina automàtica)
Aquest és l'script principal. 
*   **Què fa:** Agafa qualsevol fitxer `.xls` de la carpeta i n'elimina totes les proteccions.
*   **Com funciona:**
    *   **Fulls:** Canvia el bit de protecció (`1` -> `0`).
    *   **Macros (VBA):** Elimina completament les etiquetes de configuració de seguretat (`CMG`, `DPB`, `GC`) substituint-les per espais buits ("Voiding").
*   **Resultat:** L'Excel s'obre sense demanar contrasenya i permet veure/editar el codi VBA sense errors.

### 2. `password_recovery.py` (Recuperador de Claus)
Si necessites saber "quina era la contrasenya" per als Fulls (no per a les macros).
*   Inclou un llistat de col·lisions conegudes per al hash `0xca35` (el més comú).
*   Exemples: `anime`, `flag1`, `data!`.

### 3. `vba_hash_extractor.py` (Forensia)
Si necessites recuperar la contrasenya original del projecte VBA (per força bruta real) enlloc de simplement esborrar-la.
*   Extreu el "hash" del fitxer en format compatible amb **John the Ripper**.
*   Ús: `python vba_hash_extractor.py fitxer.xls > hash.txt`

---

## 🚀 Com fer-ho servir

1.  Copia els teus fitxers `.xls` bloquejats en aquesta carpeta.
2.  Obre una terminal (PowerShell o CMD).
3.  Executa:
    ```bash
    python excel_unlocker.py
    ```
4.  Es crearan fitxers nous acabats en `_unlocked.xls`.

---

## ⚠️ Notes Tècniques

*   Aquestes eines funcionen modificant els bits binaris del format OLE Compound Document (BIFF8).
*   **Excel Modern (.xlsx/.xlsm):** Aquests scripts NO funcionen per a fitxers nous (XML). Per a aquests, canvia l'extensió a `.zip` i edita els XML interns.
