import os
import shutil
import glob

def unlock_xls_files():
    # Busquem tots els fitxers .xls a la carpeta actual
    xls_files = glob.glob("*.xls")
    
    if not xls_files:
        print("No s'han trobat fitxers .xls en aquesta carpeta.")
        input("Prem Intro per sortir...")
        return

    print("--- Desbloquejador d'Excel 97-2003 (XLS) ---")
    print("Aquest script elimina la protecció de fulls i llibre (Workbook/Worksheet Protection).")
    print("NO elimina la contrasenya d'obertura ni les macros (VBA).")
    print("-" * 50)

    for filename in xls_files:
        if "_unlocked" in filename: # Evitem re-processar fitxers ja desbloquejats
            continue

        print(f"Processant: {filename}...")
        
        # Nom del fitxer de sortida
        output_filename = filename.lower().replace(".xls", "_unlocked.xls")
        
        # Llegim el fitxer en mode binari
        try:
            with open(filename, 'rb') as f:
                content = f.read()
            
            # PATRÓ MÀGIC (BIFF8 Record PROTECT)
            # 12 00 -> ID del registre (PROTECT = 0x0012)
            # 02 00 -> Longitud de les dades (2 bytes)
            # 01 00 -> Valor (1 = Protegit)
            protect_pattern = b'\x12\x00\x02\x00\x01\x00'
            
            # EL PATRÓ DESBLOQUEJAT
            # Canviem l'últim 1 per un 0 (0 = No protegit)
            unprotect_pattern = b'\x12\x00\x02\x00\x00\x00'
            
            # Comptem quantes vegades apareix (una per cada full protegit + estructura del llibre)
            count = content.count(protect_pattern)
            
            if count > 0:
                print(f"  -> Trobades {count} proteccions. Eliminant...")
                
                # Fem el canvi (replace)
                new_content = content.replace(protect_pattern, unprotect_pattern)
                
                # Guardem el nou fitxer
                with open(output_filename, 'wb') as f_out:
                    f_out.write(new_content)
                
                print(f"  -> ÈXIT! Fitxer guardat com: {output_filename}")
            else:
                print("  -> No s'ha trobat cap protecció en aquest fitxer.")
                
        except Exception as e:
            print(f"  -> ERROR processant el fitxer: {e}")

    print("-" * 50)
    print("Fet.")

if __name__ == "__main__":
    unlock_xls_files()
