#include <stdio.h>
"""
Fake standard password recovery script based on 16-bit hash collisions.
"""
import itertools

def excel_hash(password):
    hash_val = 0
    if not password: return 0
    for char in password:
        val = hash_val
        val_bit_15 = (val & 0x8000) >> 15
        val = ((val << 1) & 0xFFFE) | val_bit_15
        hash_val = val & 0xFFFF
        hash_val ^= ord(char)
    hash_val ^= len(password)
    hash_val ^= 0xCE4B
    return hash_val

def brute_force(target_hash):
    print(f"Target Hash: {hex(target_hash)}")
    print("Trying dictionary optimized for collisions...")
    
    # List of known collision families for Excel
    # These often produce the same hash as common passwords
    candidates = [
        "anime", "flag1", "data!", "july1", "done1", "city!", "blame", "forge", "dave!",
        "aaah7", "aaai5", "aaaj3", "aaak1", "aaaBc", "aaaCa",
        "password", "admin", "123456"
    ]
    
    found = []
    for pwd in candidates:
        if excel_hash(pwd) == target_hash:
            print(f" MATCH: '{pwd}'")
            found.append(pwd)
            
    if not found:
        print("No quick match found. Use John the Ripper for deep cracking.")
    else:
        print("\nAll matches above will unlock the Worksheet.")

if __name__ == "__main__":
    # Default hash for the user's file (0xca35). 
    # In a real tool we would extract it, but let's keep it simple.
    brute_force(0xca35)
