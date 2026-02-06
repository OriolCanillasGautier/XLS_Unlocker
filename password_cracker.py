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
import argparse
import re

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

def build_dictionary(add_variants=True):
    """Build a small, generic seed dictionary and variations."""
    base_words = [
        "excel", "sheet", "workbook", "project", "macro", "vba",
        "protect", "protected", "unlock", "security", "editor",
        "calc", "table", "data", "input", "output",
    ]

    extended = set()
    for w in base_words:
        extended.update([w, w.upper(), w.lower(), w.capitalize()])
        if add_variants:
            extended.update([
                w + "1", w + "2", w + "3",
                w + "01", w + "02",
                w + "!", w + "?",
            ])
    return list(extended)


def load_wordlist_file(path):
    """Load one wordlist file (one entry per line)."""
    words = []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                w = line.strip()
                if w:
                    words.append(w)
    except Exception:
        return []
    return words


def load_wordlists(paths, dirs):
    """Load multiple wordlists from files and directories."""
    words = []
    for p in paths:
        words.extend(load_wordlist_file(p))

    for d in dirs:
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if name.lower().endswith('.txt'):
                words.extend(load_wordlist_file(os.path.join(d, name)))

    return words


def extract_ascii_words(data, min_len=4):
    """Extract ASCII-like words from the binary data to build a context dictionary."""
    text = data.decode('latin-1', errors='ignore')
    pattern = re.compile(rf"[A-Za-z0-9][A-Za-z0-9_\-]{{{max(0, min_len - 1)},}}")
    return list(set(pattern.findall(text)))

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

def crack_hash(target_hash, algo_func, max_len=4, charset=None):
    """Brute force a hash using the given algorithm."""
    chars = charset or (string.ascii_lowercase + string.digits + string.ascii_uppercase + "!@#$")
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
    parser = argparse.ArgumentParser(description="Excel 97-2003 (.xls) password cracker")
    parser.add_argument("file", nargs='?', default="original.xls", help=".xls file to analyze")
    parser.add_argument("--wordlist", action='append', default=[], help="Path to a wordlist file (repeatable)")
    parser.add_argument("--wordlist-dir", action='append', default=[], help="Directory with .txt wordlists")
    parser.add_argument("--no-builtins", action='store_true', help="Disable built-in seed dictionary")
    parser.add_argument("--no-variants", action='store_true', help="Disable simple suffix/case variants")
    parser.add_argument("--extract-words", action='store_true', help="Extract words from the XLS binary")
    parser.add_argument("--extract-min-len", type=int, default=4, help="Minimum length for extracted words")
    parser.add_argument("--max-len", type=int, default=4, help="Max brute-force length")
    parser.add_argument("--charset", default=None, help="Custom brute-force charset")

    args = parser.parse_args()
    input_file = args.file

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
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

    dictionary = []
    if not args.no_builtins:
        dictionary.extend(build_dictionary(add_variants=not args.no_variants))

    external_words = load_wordlists(args.wordlist, args.wordlist_dir)
    if external_words:
        dictionary.extend(external_words)

    if args.extract_words:
        dictionary.extend(extract_ascii_words(data, min_len=args.extract_min_len))

    # Normalize dictionary entries
    dictionary = list({w for w in dictionary if w and isinstance(w, str)})
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
                found = crack_hash(target, algo_func, max_len=args.max_len, charset=args.charset)
                if found:
                    all_results.append((target, algo_name, found))
                    print(f"    [{algo_name}] BRUTE FORCE: '{found}'")
                else:
                    print(f"    [{algo_name}] No match (1-{args.max_len} chars).")

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
