#!/usr/bin/env python
"""
Tools to investigate the .fil files for a session.
The sessions that used fil files are considered the "old" sessions.
"""
import machines
import remote
import sys

def get_size(session):
    """
    Returns the total size in terabytes of fil files for a session.
    Prints out stuff along the way.
    """
    output = remote.retry_run_one("bls0", f"du --max-depth=0 --total /mnt_blc*/datax*/dibas*/{session}")
    for line in output:
        print(line)
    kb = int(output[-1].split()[0])
    mb = kb / 1000
    gb = mb / 1000
    tb = gb / 1000
    print(f"= {tb:.2f}T")
    return tb

def find_raw(session):
    """
    Return a list of the raw files left for this session.
    """
    return remote.retry_run_one("bls0", f"find /mnt_blc*/datax*/dibas*/{session} -name '*.raw'")

def ready(session):
    """
    Heuristically, whether we think this session is ready to reduce.
    """
    raw = find_raw(session)
    print(f"{session} has {len(raw)} .raw files.")
    if raw:
        print("for example:")
        for f in raw[:5]:
            print(f)
    for fname in raw:
        if "DIAG" in fname:
            continue
        if "/blc" in fname:
            print(f"{fname} still needs to be reduced.")
            return False
    return True

if __name__ == "__main__":
    session = sys.argv[1]
    if "AGBT" not in session:
        raise RuntimeError(f"bad session: {session}")
    print()
    get_size(session)
    print()
    assert ready(session)

