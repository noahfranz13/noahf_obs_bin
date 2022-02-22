#!/usr/bin/env python
"""
When a file has been deleted on disk, update it in the database to show that it is deleted.
This isn't supposed to happen as a part of regular operations. But when it does, we shouldn't
leave bad index data around forever.
"""

import os
import sys

import bldw

assert __name__ == "__main__"

filename = sys.argv[1]
assert not os.path.exists(filename)

conn = bldw.Connection()
meta = conn.fetch_metadata_by_filename(filename)
assert not meta.deleted
meta.deleted = True
print("updating bldw...")
conn.update_meta_deleted(meta)
print("ok")
