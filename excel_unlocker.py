import shutil
import re
import sys
import os
import glob

def unlock_file(filename):
    print(f"Processing: {filename}")
    output_filename = filename.replace(".xls", "_unlocked.xls")
    
    with open(filename, 'rb') as f:
        content = f.read()

    new_content = content
    
    # 1. UNLOCK SHEETS (Bit-Flip)
    protect_pattern = b'\x12\x00\x02\x00\x01\x00'
    unprotect_pattern = b'\x12\x00\x02\x00\x00\x00'
    
    count_sheets = new_content.count(protect_pattern)
    if count_sheets > 0:
        new_content = new_content.replace(protect_pattern, unprotect_pattern)
        print(f"  [Sheets] Removed protection from {count_sheets} elements.")

    # 2. UNLOCK VBA (Tag Voiding)
    vba_keys = [b'CMG', b'DPB', b'GC']
    found_vba = False
    
    for key in vba_keys:
        # Matches KEY="VALUE"
        pattern = key + b'="[^"]+"'
        
        def replacer(match):
            found_str = match.group(0)
            return b' ' * len(found_str)
            
        new_content, count = re.subn(pattern, replacer, new_content)
        if count > 0:
            found_vba = True

    if found_vba:
        print("  [VBA] Removed password protection tags.")
    
    with open(output_filename, 'wb') as f:
        f.write(new_content)
    print(f"  -> Created: {output_filename}\n")

def main():
    print("--- EXCEL 97-2003 UNLOCKER TOOL ---")
    files = glob.glob("*.xls")
    files = [f for f in files if "_unlocked" not in f]
    
    if not files:
        print("No .xls files found in current directory.")
        return

    for f in files:
        unlock_file(f)

if __name__ == "__main__":
    main()
