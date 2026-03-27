#!/bin/bash
# walk-the-code CI checks
set -e

echo "=== Running Python tests ==="
python3 -m unittest discover tests/ -v

echo ""
echo "=== Validating example project ==="
python3 -c "
import sys
sys.path.insert(0, 'src')
sys.argv = ['wtc-validate', 'example/config.json']
from walk_the_code.validator import validate
try:
    validate()
except SystemExit as e:
    sys.exit(e.code)
"

echo ""
echo "=== Checking JSON validity ==="
python3 -c "
import json, glob
errors = 0
for f in glob.glob('**/*.json', recursive=True):
    if 'node_modules' in f or 'data/' in f:
        continue
    try:
        json.loads(open(f).read())
    except Exception as e:
        print(f'  FAIL: {f}: {e}')
        errors += 1
if errors:
    raise SystemExit(1)
print(f'  OK: All JSON files valid')
"

echo ""
echo "=== All checks passed ==="
