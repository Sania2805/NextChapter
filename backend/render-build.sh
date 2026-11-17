#!/usr/bin/env bash
set -eu

: "${RUNTIME_TOKEN:?Set RUNTIME_TOKEN in Render Environment}"
release_url=https://api.github.com/repos/Sania2805/NextChapter-runtime/releases/tags/v1
work_dir=$(mktemp -d)
trap 'rm -f "$work_dir/release.json" "$work_dir/runtime.zip"; rmdir "$work_dir"' EXIT

curl -fsS -H "Authorization: Bearer $RUNTIME_TOKEN" "$release_url" -o "$work_dir/release.json"
asset_url=$(python - "$work_dir/release.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as release:
    for asset in json.load(release)["assets"]:
        if asset["name"] == "nextchapter-runtime.zip":
            print(asset["url"])
            break
    else:
        sys.exit("The v1 release is missing nextchapter-runtime.zip.")
PY
)
curl -fsSL -H "Authorization: Bearer $RUNTIME_TOKEN" -H 'Accept: application/octet-stream' \
    "$asset_url" -o "$work_dir/runtime.zip"
python -m zipfile -e "$work_dir/runtime.zip" .
python -m pip install -r backend/requirements.txt
python backend/surprise.py
