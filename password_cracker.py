"""
Excel 97-2003 (.xls) Password Cracker.
Scans the binary file for PASSWORD records and tries to recover
the plaintext password using multiple known hash algorithms.
"""
import os
import struct
import itertools
import string
import sys

# ============================================================
# HASH ALGORITHMS (ALL KNOWN VARIANTS)
# ============================================================

def hash_v1_standard(password):
    """Standard Excel hash: 16-bit rotate-left + XOR."""
    h = 0
    for ch in password:
        h = ((h << 1) & 0xFFFF) | ((h >> 15) & 1)
        h ^= ord(ch)
    h ^= len(password)
    h ^= 0xCE4B
    return h & 0xFFFF

def hash_v2_15bit(password):
    """Alternative: 15-bit rotate-left + XOR (OpenOffice docs)."""
    h = 0
    for ch in password:
        h = ((h << 1) & 0x7FFF) | ((h >> 14) & 1)
        h ^= ord(ch)
    h ^= len(password)
    h ^= 0xCE4B
    return h & 0xFFFF

def hash_v3_reverse(password):
    """Reverse iteration: process characters from end to start."""
    h = 0
    for ch in reversed(password):
        h = ((h << 1) & 0x7FFF) | ((h >> 14) & 1)
        h ^= ord(ch)
    h ^= len(password)
    h ^= 0xCE4B
    return h & 0xFFFF

def hash_v4_positional(password):
    """Positional: each char is rotated by its position index."""
    h = 0
    for i, ch in enumerate(password):
        char_val = ord(ch)
        rotated = ((char_val << (i + 1)) & 0x7FFF) | (char_val >> (15 - (i + 1) % 15))
        h ^= rotated & 0x7FFF
    h ^= len(password)
    h ^= 0xCE4B
    return h & 0xFFFF

def hash_v5_msdn(password):
    """MSDN documented algorithm for Excel sheet protection."""
    password_bytes = password.encode('ascii')
    h = 0
    char_index = len(password_bytes)
    for byte in password_bytes:
        intermediate = byte ^ char_index
        rot = char_index & 0x0F
        intermediate = ((intermediate << rot) | (intermediate >> (16 - rot))) & 0xFFFF
        h ^= intermediate
        char_index -= 1
    h ^= len(password_bytes)
    h ^= 0xCE4B
    return h & 0xFFFF

ALL_ALGORITHMS = {
    'v1_standard_16bit': hash_v1_standard,
    'v2_15bit':          hash_v2_15bit,
    'v3_reverse_15bit':  hash_v3_reverse,
    'v4_positional':     hash_v4_positional,
    'v5_msdn':           hash_v5_msdn,
}

# ============================================================
# DICTIONARY
# ============================================================

def build_dictionary():
    """Build a comprehensive dictionary of common passwords and variations."""
    base_words = [
        "password", "Password", "123456", "1234", "12345", "admin", "excel", "test",
        "secret", "hello", "master", "qwerty", "abc123", "letmein", "welcome",
        "monkey", "dragon", "login", "princess", "football", "shadow", "sunshine",
        "trustno1", "iloveyou", "batman", "access", "flower", "passw0rd",
        "anime", "flag1", "data", "july", "blame", "forge", "dave",
        "macro", "vba", "sheet", "lock", "unlock", "open", "close",
        # German (common in financial XLS files)
        "amort", "amor", "bank", "loan", "rate", "calc", "zins",
        "kredit", "tilgung", "darlehen", "geld", "wert", "konto",
        "tabelle", "blatt", "schutz", "passwort", "kennwort", "geheim",
        "AMORTWKZ", "amortwkz", "Amortwkz",
        # Spanish / Catalan
        "hola", "clau", "contrasenya", "taula", "full",
    ]

    extended = set()
    for w in base_words:
        extended.update([
            w, w + "1", w + "!", w + "123", w + "12",
            w.upper(), w.lower(), w.capitalize(),
        ])
    return list(extended)

# ============================================================
# SCANNER
# ============================================================

def find_password_hashes(data):
    """Find PASSWORD records (0x0013, length 2) via raw byte scan."""
    results = []
    offset = 0
    while True:
        idx = data.find(b'\x13\x00\x02\x00', offset)
        if idx == -1:
            break
        h = struct.unpack_from('<H', data, idx + 4)[0]
        results.append({'offset': idx, 'hash': h})
        offset = idx + 1
    return results

# ============================================================
# CRACKER
# ============================================================

def crack_hash(target_hash, algo_func, max_len=4):
    """Brute force a hash using the given algorithm."""
    chars = string.ascii_lowercase + string.digits + string.ascii_uppercase + "!@#$"
    for length in range(1, max_len + 1):
        for combo in itertools.product(chars, repeat=length):
            pwd = "".join(combo)
            if algo_func(pwd) == target_hash:
                return pwd
    return None

# ============================================================
# MAIN
# ============================================================

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "original.xls"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        print(f"Usage: python {os.path.basename(__file__)} <file.xls>")
        return

    with open(input_file, 'rb') as f:
        data = f.read()

    print(f"File: {input_file} ({len(data)} bytes)")
    print("=" * 60)

    # 1. Find hashes
    print("\n[STEP 1] Scanning for PASSWORD records...")
    records = find_password_hashes(data)
    unique_hashes = list(set(r['hash'] for r in records if r['hash'] != 0))

    print(f"  Found {len(records)} PASSWORD records.")
    print(f"  Unique non-zero hashes: {[hex(h) for h in unique_hashes]}")

    if not unique_hashes:
        print("\n  No password hashes found in this file.")
        return

    # 2. Crack each hash with all algorithms
    print("\n[STEP 2] Cracking hashes...")
    print("-" * 60)

    dictionary = build_dictionary()
    all_results = []  # Collect all findings here

    for target in unique_hashes:
        print(f"\n  Hash: {hex(target)}")

        for algo_name, algo_func in ALL_ALGORITHMS.items():
            # Dictionary attack
            found = None
            for pwd in dictionary:
                if algo_func(pwd) == target:
                    found = pwd
                    break

            if found:
                all_results.append((target, algo_name, found))
                print(f"    [{algo_name}] MATCH: '{found}'")
            else:
                # Brute force 1-4 chars
                found = crack_hash(target, algo_func, max_len=4)
                if found:
                    all_results.append((target, algo_name, found))
                    print(f"    [{algo_name}] BRUTE FORCE: '{found}'")
                else:
                    print(f"    [{algo_name}] No match (1-4 chars).")

    # 3. Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    if all_results:
        # Deduplicate passwords
        unique_passwords = sorted(set(pwd for _, _, pwd in all_results))

        print(f"\n  Found {len(all_results)} matches across all algorithms.")
        print(f"  Unique passwords to try: {len(unique_passwords)}\n")

        print("  Passwords found:")
        print("  " + "-" * 40)
        for pwd in unique_passwords:
            # Show which hash(es) and algorithm(s) matched
            matching = [(hex(h), algo) for h, algo, p in all_results if p == pwd]
            algos = ", ".join(f"{algo}" for _, algo in matching)
            hashes = ", ".join(set(h for h, _ in matching))
            print(f"    '{pwd}'  (hash: {hashes} | algo: {algos})")

        print("\n  Try each password above in Excel:")
        print("    Review > Unprotect Sheet > Enter password")
        print("\n  Note: Multiple passwords may work due to hash collisions.")
        print("  The 16-bit hash only has 65536 possible values,")
        print("  so different passwords can produce the same hash.")
    else:
        print("\n  No passwords found.")
        print("  The password may be longer than 4 characters or use")
        print("  special characters not in the search space.")
        print("  Consider using John the Ripper for deeper cracking.")

if __name__ == "__main__":
    main()
