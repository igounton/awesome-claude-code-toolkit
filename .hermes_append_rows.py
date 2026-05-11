#!/usr/bin/env python3
from pathlib import Path
import json, re, subprocess, sys

pr = int(sys.argv[1])
plan = {item['pr']: item['section'] for item in json.loads(Path('.hermes_merge_plan.json').read_text())}
section = plan[pr]
diff = subprocess.check_output(['gh','pr','diff',str(pr),'--patch'], stderr=subprocess.STDOUT).decode(errors='ignore')
rows = []
seen_key = {}
for line in diff.splitlines():
    if not line.startswith('+|') or line.startswith('+++'):
        continue
    row = line[1:].rstrip()
    if '---' in row or row.startswith('| Tool') or row.startswith('| Plugin') or row.startswith('| Skill') or row.startswith('| Resource') or row.startswith('| Config'):
        continue
    m = re.search(r'\]\(([^)]+)\)', row)
    key = m.group(1).split('#')[0] if m else row.split('|')[1].strip()
    if key in seen_key:
        rows[seen_key[key]] = row  # keep latest version from multi-commit diffs
    else:
        seen_key[key] = len(rows)
        rows.append(row)
if not rows:
    raise SystemExit(f'No table rows extracted for PR #{pr}')

base = subprocess.check_output(['git','show','origin/main:README.md']).decode()
lines = base.splitlines()
for row in rows:
    key_match = re.search(r'\]\(([^)]+)\)', row)
    key = key_match.group(1).split('#')[0] if key_match else None
    current = '\n'.join(lines)
    if row in current or (key and key in current):
        continue
    start = next(i for i,l in enumerate(lines) if l.strip() == section)
    end = len(lines)
    if section.startswith('### '):
        for j in range(start+1, len(lines)):
            if lines[j].startswith('### ') or lines[j].startswith('## '):
                end = j; break
    else:
        for j in range(start+1, len(lines)):
            if lines[j].startswith('## '):
                end = j; break
    insert = end
    for j in range(end-1, start, -1):
        if lines[j].strip() and lines[j].strip() != '---':
            insert = j + 1; break
    lines.insert(insert, row)
Path('README.md').write_text('\n'.join(lines) + '\n')
print(f'PR #{pr}: ensured {len(rows)} row(s) at end of {section}')
