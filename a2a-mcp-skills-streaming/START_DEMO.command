#!/bin/zsh
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo "Run the setup steps in START_HERE.md first."
  exit 1
fi
exec .venv/bin/python run.py
