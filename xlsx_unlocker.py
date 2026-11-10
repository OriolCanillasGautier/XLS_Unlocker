#!/usr/bin/env python3
"""
xlsx_unlocker.py -- OOXML (.xlsx / .xlsm) sheet-protection toolkit.

Companion to the BIFF8 tools in this repo. The legacy scripts cannot read OOXML
files (a .xlsx is a ZIP of XML parts, not an OLE/BIFF8 stream), so this module
handles the modern format.

Key point about "passwords" in .xlsx:

  A modern .xlsx is normally NOT encrypted. When someone "protects" a sheet,
  Excel writes a <sheetProtection> element into that sheet's XML:

      <sheetProtection algorithmName="SHA-512" hashValue="..." saltValue="..."
                       spinCount="100000" sheet="1" objects="1" scenarios="1"/>

  The hash is a verification aid, not a decryption key -- no data is encrypted.
  Excel compares a candidate password against the hash locally, then enforces the
  lock in the UI. Removing the element removes the lock, with zero data loss and
  no password required. (This is why password "recovery" for sheet protection is
  usually unnecessary; it is only interesting when you want the actual string,
  e.g. to reuse it on other files.)

Subcommands
  inspect   Show sheets, protection state and any recoverable hash material.
  unlock    Strip <sheetProtection> from every sheet -> new file (default action).
  protect   Apply protection to every sheet using a password YOU choose.
  verify    Test one candidate password against an existing hash.
  crack     Wordlist attack against an existing hash (multiprocessing).
  selftest  Validate the KDF against hashcat's published mode-25300 vector.

The SHA-512 KDF implemented here is the ECMA-376 agile derivation that Excel
uses for sheet protection (verified against hashcat mode 25300). Hashcat can
consume the emitted "$office$2016$0$..." lines if you have a GPU.

Usage
  python xlsx_unlocker.py inspect  target.xlsx
  python xlsx_unlocker.py unlock   target.xlsx
  python xlsx_unlocker.py unlock   target.xlsx --password "NewPass"   # re-lock
  python xlsx_unlocker.py verify   target.xlsx --password candidate
  python xlsx_unlocker.py crack    target.xlsx --wordlist list.txt --targeted
  python xlsx_unlocker.py selftest

Author: built for XLS_Unlocker.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import struct
import sys
import zipfile
from xml.sax.saxutils import escape

# --------------------------------------------------------------------------- #
# Crypto: ECMA-376 agile password-to-hash (SHA-512), as used by sheetProtection
# --------------------------------------------------------------------------- #

SPIN_COUNT_DEFAULT = 100_000
SALT_LEN = 16


def kdf_hash(password: str, salt: bytes, spin_count: int = SPIN_COUNT_DEFAULT) -> str:
    """Return base64(SHA-512 chain) exactly as Excel stores it in hashValue."""
    h = hashlib.sha512(salt + password.encode("utf-16-le")).digest()
    for i in range(spin_count):
        h = hashlib.sha512(h + struct.pack("<I", i)).digest()
    return base64.b64encode(h).decode("ascii")


def kdf_verify(password: str, salt_b64: str, spin_count: int, hash_b64: str) -> bool:
    """Constant-ish time comparison of a candidate password against stored hash."""
    try:
        salt = base64.b64decode(salt_b64, validate=True)
    except Exception:
        return False
    if len(salt) != SALT_LEN:
        return False
    candidate = kdf_hash(password, salt, spin_count)
    # compare as bytes to avoid early-exit on string compare
    return hashlib.sha512(candidate.encode()).digest() == hashlib.sha512(
        hash_b64.encode()
    ).digest()


# --------------------------------------------------------------------------- #
# Package helpers
# --------------------------------------------------------------------------- #

PROTECTION_RE = re.compile(rb"<sheetProtection\b[^>]*?/>", re.DOTALL)
PROTECTION_PAIR_RE = re.compile(
    rb"<sheetProtection\b[^>]*?>.*?</sheetProtection>", re.DOTALL
)
SHEETPROT_ATTR_RE = re.compile(rb'(\w+)="([^"]*)"')


def read_part(zf: zipfile.ZipFile, name: str) -> bytes:
    with zf.open(name) as fh:
        return fh.read()


def sheet_map(zf: zipfile.ZipFile) -> dict[str, str]:
    """Map worksheet part path -> human sheet name."""
    names = zf.namelist()
    out: dict[str, str] = {}
    if "xl/workbook.xml" not in names:
        return out
    wb = read_part(zf, "xl/workbook.xml").decode("utf-8", "replace")
    rels = ""
    if "xl/_rels/workbook.xml.rels" in names:
        rels = read_part(zf, "xl/_rels/workbook.xml.rels").decode("utf-8", "replace")

    rid_target: dict[str, str] = {}
    for m in re.finditer(r"<Relationship\b[^>]*>", rels):
        tag = m.group(0)
        rid = re.search(r'Id="([^"]*)"', tag)
        tgt = re.search(r'Target="([^"]*)"', tag)
        if rid and tgt:
            target = tgt.group(1).lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            rid_target[rid.group(1)] = target

    for m in re.finditer(r"<sheet\b[^>]*>", wb):
        tag = m.group(0)
        nm = re.search(r'name="([^"]*)"', tag)
        rid = re.search(r'r:id="([^"]*)"', tag)
        if nm and rid and rid.group(1) in rid_target:
            out[rid_target[rid.group(1)]] = nm.group(1)
    return out


def xml_unescape(s: str) -> str:
    return (
        s.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
        .replace("&amp;", "&")
    )


def find_protections(xml: bytes) -> list[dict[str, str]]:
    """Return parsed attributes of every <sheetProtection> in a sheet part."""
    found: list[dict[str, str]] = []
    for pat in (PROTECTION_RE, PROTECTION_PAIR_RE):
        for m in pat.finditer(xml):
            attrs = {
                k.decode(): xml_unescape(v.decode("utf-8", "replace"))
                for k, v in SHEETPROT_ATTR_RE.findall(m.group(0))
            }
            if attrs and attrs not in found:
                found.append(attrs)
    return found


def rewrite_package(src: str, dst: str, transform) -> None:
    """Copy every ZIP member to dst, passing sheet XML through `transform`."""
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            data = b"" if info.is_dir() else zin.read(info.filename)
            if not info.is_dir():
                data = transform(info.filename, data)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zi.internal_attr = info.internal_attr
            zi.comment = info.comment
            zout.writestr(zi, data)


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #

def cmd_inspect(args) -> int:
    path = args.file
    with zipfile.ZipFile(path) as zf:
        bad = zf.testzip()
        if bad:
            print(f"!! CORRUPT MEMBER: {bad}")
        names = zf.namelist()
        xml_parts = [n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml")]
        smap = sheet_map(zf)
        print(f"file      : {path}")
        print(f"type      : OOXML package ({len(names)} parts, {os.path.getsize(path):,} bytes)")
        kind = "macro-enabled (.xlsm)" if "xl/vbaProject.bin" in names else "no macros"
        print(f"payload   : {kind}")
        print()

        if any(n.endswith(".bin") for n in names if "EncryptedPackage" in n):
            print("!! OOXML encryption stream present -- this file IS encrypted;")
            print("   sheetProtection analysis does not apply.")
            return 2

        # workbook-level protection
        wb = read_part(zf, "xl/workbook.xml").decode("utf-8", "replace")
        wbprot = re.search(r"<workbookProtection\b[^>]*>", wb)
        print("workbook  : " + ("PROTECTED -> " + wbprot.group(0) if wbprot else "no workbook protection"))
        if "xl/settings.xml" in names:
            st = read_part(zf, "xl/settings.xml").decode("utf-8", "replace")
            dprot = re.search(r"<documentProtection\b[^>]*>", st)
            if dprot:
                print("docProtect: " + dprot.group(0))
        print()

        any_prot = False
        for part in sorted(xml_parts):
            label = smap.get(part, part)
            xml = read_part(zf, part)
            prots = find_protections(xml)
            if not prots:
                print(f"  [open]   {label:<16} {part}")
                continue
            any_prot = True
            print(f"  [LOCKED] {label:<16} {part}")
            for p in prots:
                algo = p.get("algorithmName", "legacy 16-bit")
                spin = p.get("spinCount", "-")
                print(f"           algorithm : {algo}")
                print(f"           spinCount : {spin}")
                if p.get("saltValue"):
                    print(f"           saltValue : {p['saltValue']}")
                if p.get("hashValue"):
                    print(f"           hashValue : {p['hashValue'][:32]}... ({len(p['hashValue'])} chars)")
                    if p.get("saltValue") and spin.isdigit():
                        line = (
                            f"$office$2016$0${spin}${p['saltValue']}${p['hashValue']}"
                        )
                        print(f"           hashcat   : {line}")
                if p.get("password"):
                    print(f"           legacy pw : {p['password']} (16-bit, trivially cracked)")
        print()
        print("summary   : " + ("protection present" if any_prot else "no sheet protection found"))
        if any_prot:
            print("            the lock is a flag + hash only -- no data is encrypted.")
            print("            'unlock' removes it with no password needed.")
    return 0


def cmd_unlock(args) -> int:
    src = args.file
    base, ext = os.path.splitext(src)
    out = args.out or (base + "_unlocked" + ext)
    if os.path.abspath(out) == os.path.abspath(src):
        print("!! refusing to overwrite the input file")
        return 2

    touched: list[str] = []
    new_pw = args.password

    # Optional restriction to named sheets (by name or part path).
    targets: set[str] | None = None
    if args.sheet:
        with zipfile.ZipFile(src) as zf:
            smap = sheet_map(zf)
        targets = set()
        for want in args.sheet:
            hit = {p for p, n in smap.items() if n == want}
            if not hit:
                hit = {p for p, n in smap.items() if n.lower() == want.lower()}
            if not hit and want in smap:
                hit = {want}
            if not hit:
                print(f"!! no sheet named {want!r}")
                print(f"   available: {', '.join(sorted(smap.values()))}")
                return 2
            targets |= hit
        print("target(s) : " + ", ".join(smap.get(p, p) for p in sorted(targets)))

    def transform(name: str, data: bytes) -> bytes:
        if not (name.startswith("xl/worksheets/") and name.endswith(".xml")):
            return data
        if targets is not None and name not in targets:
            return data
        before = find_protections(data)
        had = bool(before)
        data2 = PROTECTION_PAIR_RE.sub(b"", data)
        data2 = PROTECTION_RE.sub(b"", data2)
        if new_pw is not None:
            # Re-protect with a password the user chose.
            salt = os.urandom(SALT_LEN)
            hv = kdf_hash(new_pw, salt, SPIN_COUNT_DEFAULT)
            elem = (
                '<sheetProtection algorithmName="SHA-512" hashValue="{}" '
                'saltValue="{}" spinCount="{}" sheet="1" objects="1" '
                'scenarios="1"/>'.format(
                    hv, base64.b64encode(salt).decode("ascii"), SPIN_COUNT_DEFAULT
                )
            ).encode("ascii")
            if b"</sheetData>" in data2:
                data2 = data2.replace(b"</sheetData>", b"</sheetData>" + elem, 1)
            else:
                raise RuntimeError(
                    f"{name}: no </sheetData> anchor; cannot re-protect safely"
                )
        if had or new_pw is not None:
            touched.append(name)
        return data2

    rewrite_package(src, out, transform)

    # verify result
    with zipfile.ZipFile(out) as zf:
        bad = zf.testzip()
        if bad:
            print(f"!! output corrupt at {bad}")
            return 3
        remaining = 0
        for n in zf.namelist():
            if n.startswith("xl/worksheets/") and n.endswith(".xml"):
                remaining += len(find_protections(read_part(zf, n)))

    print(f"input     : {src}")
    print(f"output    : {out}")
    print(f"parts edit: {len(touched)}")
    print(f"remaining : {remaining} protection element(s)")
    if new_pw is None:
        print("status    : UNLOCKED (protection removed, all data preserved)")
    else:
        print("status    : re-protected with the supplied password")
    return 0


def cmd_verify(args) -> int:
    with zipfile.ZipFile(args.file) as zf:
        for part, xml in _iter_sheets(zf):
            for p in find_protections(xml):
                if not p.get("saltValue"):
                    print(f"{part}: legacy hash, use password_cracker.py")
                    continue
                ok = kdf_verify(
                    args.password, p["saltValue"], int(p["spinCount"]), p["hashValue"]
                )
                print(f"{part}: {'MATCH' if ok else 'no match'} for {args.password!r}")
    return 0


def _iter_sheets(zf: zipfile.ZipFile):
    for n in zf.namelist():
        if n.startswith("xl/worksheets/") and n.endswith(".xml"):
            yield n, read_part(zf, n)


def _hash_job(job):
    idx, pw, salt_b64, spin, target_b64 = job
    return (idx, pw) if kdf_verify(pw, salt_b64, spin, target_b64) else None


def cmd_crack(args) -> int:
    import multiprocessing as mp

    target = None
    with zipfile.ZipFile(args.file) as zf:
        for part, xml in _iter_sheets(zf):
            for p in find_protections(xml):
                if p.get("saltValue") and p.get("hashValue"):
                    target = (part, p["saltValue"], int(p["spinCount"]), p["hashValue"])
                    break
            if target:
                break
    if not target:
        print("no SHA-512 protected sheet found in file")
        return 2

    part, salt_b64, spin, hash_b64 = target
    print(f"target    : {part}")
    print(f"spinCount : {spin}")

    candidates: list[str] = []
    seen: set[str] = set()

    def add(seq):
        for c in seq:
            if c and c not in seen:
                seen.add(c)
                candidates.append(c)

    for wl in args.wordlist or []:
        with open(wl, "r", encoding="utf-8", errors="replace") as fh:
            add(line.rstrip("\r\n") for line in fh)

    if args.targeted:
        gen = targeted_candidates(args.file)
        print(f"targeted  : {len(gen)} generated candidates")
        add(gen)

    if not candidates:
        print("no candidates; pass --wordlist FILE or --targeted")
        return 2

    print(f"candidates: {len(candidates):,}")
    procs = args.jobs or (os.cpu_count() or 1)
    print(f"workers   : {procs}")
    print("working...")

    jobs = [
        (i, pw, salt_b64, spin, hash_b64) for i, pw in enumerate(candidates)
    ]
    found = None
    done = 0
    with mp.Pool(procs) as pool:
        try:
            for res in pool.imap_unordered(_hash_job, jobs, chunksize=2):
                done += 1
                if res is not None:
                    found = res[1]
                    pool.terminate()
                    break
                if done % 25 == 0 or done == len(jobs):
                    print(f"\r  {done}/{len(jobs)} tried", end="", flush=True)
        except KeyboardInterrupt:
            pool.terminate()
            print("\ninterrupted")
            return 130
    print()
    if found is not None:
        print(f"PASSWORD FOUND: {found!r}")
        return 0
    print("not found in the supplied candidate set")
    return 1


# --------------------------------------------------------------------------- #
# Candidate generation from file metadata (targeted wordlist)
# --------------------------------------------------------------------------- #

def targeted_candidates(path: str) -> list[str]:
    """Build plausible passwords from document metadata and sheet names."""
    words: set[str] = set()
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            blob = ""
            for n in ("docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"):
                if n in names:
                    blob += read_part(zf, n).decode("utf-8", "replace")
            blob += read_part(zf, "xl/workbook.xml").decode("utf-8", "replace")
            for val in re.findall(r">([^<>]{2,60})<", blob):
                val = xml_unescape(val).strip()
                if val and not val.startswith("{"):
                    words.add(val)
            for n in names:
                if n.startswith("xl/worksheets/") and n.endswith(".xml"):
                    for nm in re.findall(r'name="([^"]*)"', read_part(zf, n).decode("utf-8", "replace")):
                        if len(nm) < 40:
                            words.add(xml_unescape(nm))
    except Exception:
        pass

    tokens: set[str] = set()
    for w in words:
        for t in re.split(r"[\s\-_.,;/\\()\[\]{}:]+", w):
            t = t.strip()
            if 2 <= len(t) <= 30:
                tokens.add(t)
    # author names are the highest-value guess
    tokens |= {"Guillem", "Senmarti", "Senmartí", "GuillemSenmarti", "GSenmarti"}

    out: list[str] = []
    seen: set[str] = set()

    def push(s: str):
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    years = ["2024", "2025", "2026", "24", "25", "26"]
    suffixes = ["", "1", "01", "12", "123", "1234", "!", ".", "2025", "2026", "@123"]
    bases = sorted(tokens, key=len, reverse=True)

    for b in bases:
        for v in {b, b.lower(), b.upper(), b.capitalize()}:
            for suf in suffixes:
                push(v + suf)
        for y in years:
            push(b + y)
            push(b.lower() + y)

    # combos of two frequent tokens
    common = [t for t in bases if len(t) >= 4][:12]
    for a in common:
        for b in common:
            if a != b:
                push(a + b)
                push(a.capitalize() + b.capitalize())
    print(f"[targeted] metadata tokens: {', '.join(sorted(bases)[:12])}")
    return out


# --------------------------------------------------------------------------- #
# Self test against hashcat's published vector (mode 25300)
# --------------------------------------------------------------------------- #

HASHCAT_VECTOR = {
    "password": "hashcat",
    "salt": "876MLoKTq42+/DLp415iZQ==",
    "hash": "TNDvpvYyvlSUy97UOLKNhXynhUDDA7H8kLql0ISH5SxcP6hbthdjaTo4Z3/MU0dcR2SAd+AduYb3TB5CLZ8+ow==",
    "spin": 100000,
}


def cmd_selftest(args) -> int:
    import time

    print("validating KDF against hashcat mode 25300 test vector...")
    t0 = time.time()
    ok = kdf_verify(
        HASHCAT_VECTOR["password"],
        HASHCAT_VECTOR["salt"],
        HASHCAT_VECTOR["spin"],
        HASHCAT_VECTOR["hash"],
    )
    dt = time.time() - t0
    print(f"  vector match   : {'PASS' if ok else 'FAIL'}")
    print(f"  speed          : {dt:.3f}s per candidate ({1/dt:.1f}/s/core)")

    bad = kdf_verify(
        "wrong", HASHCAT_VECTOR["salt"], HASHCAT_VECTOR["spin"], HASHCAT_VECTOR["hash"]
    )
    print(f"  negative test  : {'PASS' if not bad else 'FAIL'}")
    return 0 if ok and not bad else 1


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(
        description="OOXML (.xlsx/.xlsm) sheet-protection toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd")

    p_in = sub.add_parser("inspect", help="show sheets and protection state")
    p_in.add_argument("file")
    p_in.set_defaults(func=cmd_inspect)

    p_un = sub.add_parser("unlock", help="strip protection (or re-lock with new password)")
    p_un.add_argument("file")
    p_un.add_argument("-o", "--out")
    p_un.add_argument("-p", "--password", help="re-protect every sheet with this password")
    p_un.add_argument(
        "-s",
        "--sheet",
        action="append",
        help="limit to named sheet(s); repeatable (default: all sheets)",
    )
    p_un.set_defaults(func=cmd_unlock)

    p_ve = sub.add_parser("verify", help="test a candidate password")
    p_ve.add_argument("file")
    p_ve.add_argument("-p", "--password", required=True)
    p_ve.set_defaults(func=cmd_verify)

    p_cr = sub.add_parser("crack", help="wordlist attack")
    p_cr.add_argument("file")
    p_cr.add_argument("-w", "--wordlist", action="append")
    p_cr.add_argument("--targeted", action="store_true", help="generate candidates from metadata")
    p_cr.add_argument("-j", "--jobs", type=int)
    p_cr.set_defaults(func=cmd_crack)

    p_st = sub.add_parser("selftest", help="validate the KDF")
    p_st.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    if getattr(args, "file", None) and not os.path.isfile(args.file):
        print(f"no such file: {args.file}")
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
