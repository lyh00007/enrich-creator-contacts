"""Read an exported creator list without applying prospecting filters."""
import argparse
import csv
import datetime as dt
import json
import re
from collections import OrderedDict
from pathlib import Path
from urllib.parse import unquote, urlparse

HANDLE_ALIASES = {'达人昵称', '达人账号', '达人用户名', '用户名', '账号', 'tiktok账号', 'tiktok用户名', 'handle', 'username', 'creatorusername', 'creatorhandle', 'tiktokusername', 'tiktokhandle'}
URL_ALIASES = {'主页链接', '达人主页', 'tiktok主页', '主页url', 'profileurl', 'creatorurl', 'tiktokurl', 'tiktokprofile', 'profilelink'}
VIDEO_ALIASES = {'视频id', 'videoid'}
KEY = lambda s: re.sub(r'[\s_\-]+', '', str(s or '')).lower()
HANDLE_ALIASES = {KEY(s) for s in HANDLE_ALIASES}
URL_ALIASES = {KEY(s) for s in URL_ALIASES}

def text(v):
    if v is None:
        return ''
    if isinstance(v, (dt.datetime, dt.date)):
        return v.isoformat()
    return str(v).strip()

def handle(value, allow_numeric=False):
    value = text(value)
    if not value:
        return None
    if 'tiktok.com/' in value.lower():
        parsed = urlparse(value if '://' in value else 'https://' + value)
        if (parsed.hostname or '').lower() not in {'tiktok.com', 'www.tiktok.com', 'm.tiktok.com'}:
            return None
        match = re.match(r'^/@([^/]+)(?:/|$)', unquote(parsed.path))
        if not match:
            return None
        value = match.group(1)
    else:
        if '://' in value or '/' in value:
            return None
        value = value.lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9_.]{2,24}', value):
        return None
    if value.isdigit() and len(value) >= 16 and not allow_numeric:
        return None
    return value.lower()

def load(path, sheet):
    if path.suffix.lower() == '.xlsx':
        try:
            import openpyxl
        except ImportError as e:
            raise SystemExit('XLSX reading requires openpyxl or conversion through the available spreadsheet tool.') from e
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if sheet:
            if sheet not in book.sheetnames:
                raise SystemExit('Unknown sheet. Available: ' + ', '.join(book.sheetnames))
            tab = book[sheet]
        elif len(book.sheetnames) == 1:
            tab = book.worksheets[0]
        else:
            raise SystemExit('Multiple sheets: select --sheet from ' + ', '.join(book.sheetnames))
        tab.reset_dimensions()  # Some exports incorrectly declare A1:A1.
        rows = [list(r) for r in tab.iter_rows(values_only=True)]
        name = tab.title
        book.close()
        return name, rows
    if path.suffix.lower() not in {'.csv', '.tsv', '.txt'}:
        raise SystemExit('Convert unsupported input to XLSX, CSV or TSV first.')
    raw = path.read_bytes()
    for encoding in ('utf-8-sig', 'utf-16', 'gb18030'):
        try:
            content = raw.decode(encoding)
            break
        except UnicodeError:
            continue
    else:
        raise SystemExit('Cannot determine text encoding safely.')
    delimiter = '\t' if path.suffix.lower() == '.tsv' else None
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(content[:16000], delimiters=',\t;').delimiter
        except csv.Error:
            delimiter = ','
    return '', list(csv.reader(content.splitlines(), delimiter=delimiter))

def column(headers, explicit, aliases):
    if explicit:
        if re.fullmatch(r'#\d+', explicit):
            n = int(explicit[1:]) - 1
            if n < 0 or n >= len(headers):
                raise SystemExit('Column number is outside input width.')
            return n
        matches = [i for i, h in enumerate(headers) if KEY(h) == KEY(explicit)]
    else:
        matches = [i for i, h in enumerate(headers) if KEY(h) in aliases]
    if len(matches) > 1:
        raise SystemExit('Ambiguous columns: ' + ', '.join(headers[i] for i in matches))
    if explicit and not matches:
        raise SystemExit('Requested column not found: ' + explicit)
    return matches[0] if matches else None

def normalize(args):
    path = args.input.resolve()
    sheet, rows = load(path, args.sheet)
    if args.header_row is None:
        options = [i for i, r in enumerate(rows[:30]) if any(KEY(v) in HANDLE_ALIASES | URL_ALIASES for v in r)]
        if not options:
            raise SystemExit('No safe account header found. Specify --header-row and --handle-column; for a headerless list use --header-row 0 --handle-column #1.')
        header_index = options[0]
    else:
        header_index = args.header_row - 1
    if header_index < -1 or header_index >= len(rows):
        raise SystemExit('Invalid header row.')
    width = max((len(r) for r in rows), default=0)
    headers = [text(v) or f'column_{i+1}' for i, v in enumerate(rows[header_index])] if header_index >= 0 else [f'column_{i+1}' for i in range(width)]
    if len(set(headers)) != len(headers):
        raise SystemExit('Duplicate input headers; resolve explicitly before import.')
    hc = column(headers, args.handle_column, HANDLE_ALIASES)
    uc = column(headers, args.url_column, URL_ALIASES)
    vc = column(headers, None, {KEY(x) for x in VIDEO_ALIASES})
    if hc is None and uc is None:
        raise SystemExit('No safe username/profile column. Available: ' + ', '.join(headers))
    identity_columns = {headers[i] for i in (hc, uc) if i is not None}
    def payload(values):
        return {k: v for k, v in values.items() if k not in identity_columns}
    creators, unmapped, identified, source_count = OrderedDict(), [], 0, 0
    for index, row in enumerate(rows[header_index+1:], header_index+2):
        if not any(text(v) for v in row):
            continue
        source_count += 1
        row = row + [None] * (len(headers)-len(row))
        values = {h: text(row[i]) for i, h in enumerate(headers)}
        ref = {'file': path.name, 'sheet': sheet, 'row': index}
        hv = handle(row[hc], args.allow_numeric_handles) if hc is not None else None
        uv = handle(row[uc], args.allow_numeric_handles) if uc is not None else None
        raw = {'source': ref, 'values': values}
        if hv and uv and hv != uv:
            unmapped.append({**raw, 'reason': 'Username and profile URL disagree; identity unresolved'})
            continue
        h = uv or hv
        if not h:
            unmapped.append({**raw, 'reason': 'Missing/invalid username, numeric ID or non-unique display name; do not guess'})
            continue
        identified += 1
        c = creators.setdefault(h, {'handle': h, 'profile_url': 'https://www.tiktok.com/@'+h, 'source_refs': [], 'records': [], 'warnings': [], 'status': 'pending'})
        c['source_refs'].append(ref)
        vid = text(row[vc]) if vc is not None else ''
        if args.grain == 'video' and vid and vid != '0':
            prior = [r for r in c['records'] if r.get('video_id') == vid]
            if prior and any(payload(r['values']) == payload(values) for r in prior):
                c['warnings'].append(f'Equivalent duplicate video row {index} after username normalization; retained source reference, excluded duplicate record')
                continue
            if prior:
                c['warnings'].append(f'Conflicting snapshots for video {vid}; do not sum without resolving')
        elif args.grain == 'video':
            c['warnings'].append(f'Row {index} has no valid video ID; duplicate risk')
        elif c['records']:
            c['warnings'].append('Multiple creator-level rows; preserve snapshots, do not sum')
        c['records'].append({**raw, 'video_id': vid})
    return {'sources': [{'file': path.name, 'sheet': sheet, 'grain': args.grain, 'header_row': header_index+1}], 'stats': {'source_rows': source_count, 'identified_rows': identified, 'missing_identity_rows': len(unmapped), 'unique_creators': len(creators)}, 'creators': list(creators.values()), 'unmapped': unmapped}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--sheet')
    p.add_argument('--header-row', type=int)
    p.add_argument('--handle-column')
    p.add_argument('--url-column')
    p.add_argument('--grain', choices=['video', 'creator'], required=True)
    p.add_argument('--allow-numeric-handles', action='store_true')
    args = p.parse_args()
    data = normalize(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(data['stats'], ensure_ascii=False))

if __name__ == '__main__':
    main()
