#!/bin/bash
set -e
./pipeline.py run --phase=move --host=bls$1 2>&1 | tee -a ~/pipeline.log

