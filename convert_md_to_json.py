import re
import json
import os
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed


def parse_md_items(filepath):
    items = []
    current = None
    multi_key = None
    multi_lines = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for raw in lines:
        line = raw.strip()

        m = re.match(r'^###\s+(.+)$', line)
        if m:
            if current is not None:
                if multi_key:
                    current[multi_key] = '\n'.join(multi_lines)
                    multi_key = None
                    multi_lines = []
                items.append(current)
            current = {'name': m.group(1).strip()}
            continue

        if current is None:
            continue

        m = re.match(r'^- \*\*(.+?)\*\*: ?(.*)$', line)
        if m:
            if multi_key:
                current[multi_key] = '\n'.join(multi_lines)
                multi_key = None
                multi_lines = []
            key = m.group(1).strip()
            val = m.group(2).strip()
            if val:
                current[key] = val
            else:
                multi_key = key
                multi_lines = []
            continue

        if multi_key is not None and (line.startswith('- ') or line.startswith('  ') or line.startswith('\t')):
            multi_lines.append(line)
            continue

        if line and not line.startswith('#') and not line.startswith('---') and not line.startswith('>') and not line.startswith('|'):
            if multi_key:
                current[multi_key] = '\n'.join(multi_lines)
                multi_key = None
                multi_lines = []

    if current is not None:
        if multi_key:
            current[multi_key] = '\n'.join(multi_lines)
        items.append(current)

    return items


def convert_file(input_path, output_dir):
    items = parse_md_items(input_path)
    stem = Path(input_path).stem

    # Assign sequential integer IDs per file, starting from 1
    for idx, item in enumerate(items, start=1):
        item['id'] = idx
        item['_src_id'] = item.pop('ID', None)

    output_path = os.path.join(output_dir, f'{stem}.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    return stem, len(items)


def main():
    input_root = sys.argv[1] if len(sys.argv) > 1 else 'plan/stuff'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'items-db'

    os.makedirs(output_dir, exist_ok=True)

    files = sorted(Path(input_root).glob('*.md'))
    if not files:
        print(f"No .md files found in {input_root}")
        return

    total = 0
    completed = 0
    failed = 0

    with ProcessPoolExecutor(max_workers=10) as executor:
        fut_map = {executor.submit(convert_file, str(f), output_dir): f for f in files}
        for fut in as_completed(fut_map):
            f = fut_map[fut]
            try:
                stem, count = fut.result()
                print(f"  [OK] {stem}.json  ({count} items)")
                total += count
                completed += 1
            except Exception as e:
                print(f"  [FAIL] {f.stem}: {e}")
                failed += 1

    print(f"\nDone: {completed} files, {total} items, {failed} failed")


if __name__ == '__main__':
    main()
