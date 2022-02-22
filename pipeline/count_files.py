#!/usr/bin/env python

import bldw

assert __name__ == "__main__"

c = bldw.Connection()
gb_count = c.count_where("bl.data", "location LIKE %s", ("file://gb%",))
print("Green Bank files:", gb_count)
pd_count = c.count_where("bl.data", "location LIKE %s", ("file://pd%",))
print("Berkeley files:", pd_count)
no_obs_count = c.count_where("bl.data", "observation_id IS NULL")
print("files with no observation:", no_obs_count)
berkeley_size = c.total_size_where("location LIKE %s", ("file://pd%",))
print(f"data stored at Berkeley: {berkeley_size/1000000000000:.1f}T")
