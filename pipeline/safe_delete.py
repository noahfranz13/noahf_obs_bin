#!/usr/bin/env python
"""
Deletes a file only after checking that this isn't the last copy of the file.
Usage: safe_delete.py <file>
"""

import os
import sys

import bldw

assert __name__ == "__main__"

filename = sys.argv[1]
filename = os.path.normpath(filename)

if not os.path.exists(filename):
    print(filename, "has already been deleted. perhaps we are racing another cleaner?")
    sys.exit(0)

if not os.path.isfile(filename):
    print("error:", filename, "is not a file")
    sys.exit(1)

print("checking metadata for", filename)
conn = bldw.Connection()
try:
    meta = conn.fetch_metadata_by_filename(filename)
except LookupError:
    print("no metadata exists for this file. we cannot delete it.")
    sys.exit(0)

if meta.deleted:
    print("error: this file is supposed to already be deleted. feel free to rm it")
    sys.exit(1)
    
metas = conn.fetch_metadata_by_size(meta.size)
# Check to see if we have a copy of this data elsewhere
for m in metas:
    if m.deleted:
        continue
    if m.id == meta.id:
        continue
    if m.same_data(meta):
        print("it is safe to delete", filename, "because we have a copy at", m.location)
        break
else:
    print("we have no other copy of this data, and cannot delete it.")
    sys.exit(0)

print(f"marking {filename} as deleted in bldw...")
meta.deleted = True
conn.update_meta_deleted(meta)
print("ok")
print(f"deleting {filename} from disk...")
os.remove(filename)
print("done")

