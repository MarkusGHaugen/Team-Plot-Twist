#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv using the link in README.md, then run this launcher again.'
  exit 1
fi
uv sync --locked
exec uv run streamlit run app.py --server.port 8535
