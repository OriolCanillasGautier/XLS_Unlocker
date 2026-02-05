#!/usr/bin/env python3
import sys
import re
import os

def process_file(filename):
    try:
        with open(filename, 'rb') as f:
            data = f.read()
    except IOError:
        sys.stderr.write(f"Could not open {filename}\n")
        return

    def get_tag_value(tag, data):
        pattern = tag + b'="([0-9A-Fa-f]+)"'
        match = re.search(pattern, data)
        if match:
            return match.group(1).decode('ascii')
        return None

    cmg = get_tag_value(b'CMG', data)
    dpb = get_tag_value(b'DPB', data)
    gc = get_tag_value(b'GC', data)

    if cmg and dpb and gc:
        bn = os.path.basename(filename)
        output = f"{bn}:$vba$v*1*{cmg}*{dpb}*{gc}"
        print(output)
    else:
        sys.stderr.write(f"{filename}: could not find all VBA tags\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vba_hash_extractor.py <file.xls>")
    else:
        for f in sys.argv[1:]:
            process_file(f)
