"""Validate coverage, public contact evidence and an optional contact workbook."""
import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse

STAGES = {'profile', 'bio_links', 'associated_accounts', 'targeted_search'}
STATUSES = {'pending', 'email_found', 'other_contact', 'needs_review', 'not_found_public', 'blocked_login', 'page_unavailable', 'identity_unresolved'}
OWNERSHIP = {'direct_profile', 'linked_from_profile', 'official_identity_verified'}
EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$')

def http(value):
    p = urlparse(str(value or ''))
    return p.scheme in {'http', 'https'} and bool(p.hostname)

def iso(value):
    try:
        dt.date.fromisoformat(str(value))
        return True
    except ValueError:
        return False

def validate(source, result, allow_incomplete=False):
    errors, warnings, emails = [], [], collections.defaultdict(set)
    expected = [r['handle'].lower() for r in source['creators']]
    rows = result.get('creators', [])
    actual = [str(r.get('handle', '')).lower() for r in rows]
    if len(set(expected)) != len(expected):
        errors.append('Input contains duplicate normalized handles')
    if len(set(actual)) != len(actual):
        errors.append('Results contain duplicate handles')
    if set(expected) != set(actual):
        errors.append({'coverage': {'missing': sorted(set(expected)-set(actual)), 'unexpected': sorted(set(actual)-set(expected))}})
    for row in rows:
        h, status = row.get('handle'), row.get('status')
        if status not in STATUSES:
            errors.append(f'{h}: unknown status {status}')
        if status in {'pending', 'blocked_login', 'page_unavailable', 'identity_unresolved'}:
            (warnings if allow_incomplete else errors).append(f'{h}: incomplete research ({status})')
        good_emails, other = 0, 0
        for c in row.get('contacts', []):
            value = str(c.get('value', ''))
            if c.get('kind') not in {'email', 'whatsapp', 'business_phone', 'contact_form', 'business_social', 'agency_contact'}:
                errors.append(f'{h}: unknown contact kind')
            if not value or not http(c.get('source_url')) or not str(c.get('evidence', '')).strip():
                errors.append(f'{h}: contact lacks value, source URL or evidence')
            if not iso(c.get('access_date')):
                errors.append(f'{h}: missing/invalid contact date')
            if c.get('verified_public') is not True or c.get('public_business') is not True or c.get('ownership') not in OWNERSHIP:
                errors.append(f'{h}: unverified/non-business contact belongs in leads')
            if not c.get('source_type'):
                errors.append(f'{h}: missing contact source type')
            if c.get('source_type') == 'profile_bio' and c.get('ownership') == 'direct_profile':
                parsed = urlparse(str(c.get('source_url')))
                if (parsed.hostname or '').lower() not in {'tiktok.com', 'www.tiktok.com', 'm.tiktok.com'} or parsed.path.rstrip('/').lower() != '/@'+str(h).lower():
                    errors.append(f'{h}: direct TikTok email source points to another identity')
            if c.get('kind') == 'email':
                if not EMAIL.fullmatch(value) or 'instagram-@' in value.lower():
                    errors.append(f'{h}: incomplete or invalid email')
                elif value.lower() not in str(c.get('evidence', '')).lower():
                    errors.append(f'{h}: email is not in its evidence')
                else:
                    good_emails += 1
                    emails[value.lower()].add(h)
                if value.lower().endswith('@gmal.com'):
                    errors.append(f'{h}: suspected misspelling must be a needs_review lead')
            else:
                other += 1
            if c.get('kind') == 'whatsapp' and not (c.get('whatsapp_explicit') is True or 'wa.me/' in str(c.get('source_url'))):
                errors.append(f'{h}: WhatsApp was not explicitly established')
        if status == 'email_found' and not good_emails:
            errors.append(f'{h}: email_found without supported complete email')
        if status == 'other_contact' and not other:
            errors.append(f'{h}: other_contact without verified other contact')
        if status == 'needs_review' and not row.get('leads'):
            errors.append(f'{h}: needs_review without a recorded lead')
        checks = row.get('checks', [])
        for c in checks:
            if c.get('stage') not in STAGES or c.get('outcome') not in {'completed', 'not_applicable', 'blocked'}:
                errors.append(f'{h}: invalid check stage/outcome')
            if c.get('outcome') == 'not_applicable':
                if not c.get('reason'):
                    errors.append(f'{h}: not_applicable needs a reason')
            elif not http(c.get('url')):
                errors.append(f'{h}: check needs a valid visited URL')
        if status == 'not_found_public':
            completed = {c.get('stage') for c in checks if c.get('outcome') in {'completed', 'not_applicable'}}
            if completed != STAGES or any(c.get('outcome') == 'blocked' for c in checks):
                errors.append(f'{h}: not_found_public overstates research coverage')
            if not any(c.get('stage') == 'profile' and c.get('outcome') == 'completed' for c in checks):
                errors.append(f'{h}: profile must actually be checked')
        for lead in row.get('leads', []):
            if not lead.get('value') or not lead.get('reason') or not http(lead.get('source_url')):
                errors.append(f'{h}: incomplete lead record')
    shared = {e: sorted(hs) for e, hs in emails.items() if len(hs) > 1}
    if shared:
        warnings.append({'shared_emails': shared})
    stats = source.get('stats', {})
    if stats.get('identified_rows', 0)+stats.get('missing_identity_rows', 0) != stats.get('source_rows', 0):
        errors.append('Source row reconciliation failed')
    return {'errors': errors, 'warnings': warnings, 'input_creators': len(expected), 'result_creators': len(actual), 'statuses': dict(collections.Counter(r.get('status') for r in rows)), 'unique_public_emails': len(emails), 'shared_emails': shared}

def check_workbook(path, source, result):
    try:
        import openpyxl
    except ImportError as e:
        raise SystemExit('Workbook validation requires openpyxl or equivalent checks through the spreadsheet tool.') from e
    errors = []
    book = openpyxl.load_workbook(path, data_only=False)
    if not {'达人联系表', '数据来源'} <= set(book.sheetnames):
        return ['Workbook is missing main/source sheet']
    s = book['达人联系表']
    header_row = next((i for i in range(1, min(s.max_row,30)+1) if '达人昵称' in [c.value for c in s[i]]), None)
    if not header_row:
        return ['Workbook has no creator header']
    headers = {c.value: c.column for c in s[header_row] if c.value}
    required = {'达人昵称', '主页链接', '公开商务邮箱', '其他合作入口', '查找状态', '跟进状态'}
    if not required <= set(headers):
        return ['Workbook lacks required contact columns']
    found = []
    supported = {r['handle'].lower(): {c['value'].lower() for c in r.get('contacts', []) if c.get('kind') == 'email'} for r in result['creators']}
    for row in s.iter_rows(min_row=header_row+1):
        h = str(row[headers['达人昵称']-1].value or '').strip().lower()
        if not h:
            continue
        found.append(h)
        u = row[headers['主页链接']-1]
        expected_url = 'https://www.tiktok.com/@'+h
        if u.value != expected_url or not u.hyperlink or u.hyperlink.target != expected_url:
            errors.append(f'{h}: profile URL must be visible and natively clickable')
        es = str(row[headers['公开商务邮箱']-1].value or '')
        parts = {x.strip().lower() for x in re.split(r'[;；\n]+', es) if x.strip()}
        if parts != supported.get(h, set()):
            errors.append(f'{h}: workbook emails differ from research results')
    if len(found) != len(set(found)) or set(found) != {r['handle'].lower() for r in source['creators']}:
        errors.append('Workbook account coverage mismatch')
    evidence_sheet = book['数据来源']
    erow = next((i for i in range(1, min(evidence_sheet.max_row,30)+1) if '达人昵称' in [c.value for c in evidence_sheet[i]]), None)
    if not erow:
        errors.append('Source sheet has no creator header')
    else:
        cols = {c.value: c.column for c in evidence_sheet[erow] if c.value}
        if not {'达人昵称', '来源URL', '证据'} <= set(cols):
            errors.append('Source sheet lacks identity, URL or evidence columns')
        else:
            identities = {str(evidence_sheet.cell(i,cols['达人昵称']).value or '').lower() for i in range(erow+1,evidence_sheet.max_row+1)}
            if not set(found) <= identities:
                errors.append('Source sheet does not cover all input creators')
            for r in result['creators']:
                for contact in r.get('contacts', []):
                    matched = [i for i in range(erow+1,evidence_sheet.max_row+1) if str(evidence_sheet.cell(i,cols['达人昵称']).value or '').lower()==r['handle'].lower() and evidence_sheet.cell(i,cols['来源URL']).value==contact['source_url'] and str(contact['value']).lower() in str(evidence_sheet.cell(i,cols['证据']).value or '').lower()]
                    if not matched:
                        errors.append(f"{r['handle']}: contact evidence is absent from source sheet")
                    for i in matched:
                        cell=evidence_sheet.cell(i,cols['来源URL'])
                        if not cell.hyperlink or cell.hyperlink.target!=cell.value:
                            errors.append(f"{r['handle']}: source URL lacks native hyperlink")
    if source.get('unmapped') and '缺少账号记录' not in book.sheetnames:
        errors.append('Missing unidentified-source-rows sheet')
    for tab in book:
        if any(c.data_type == 'e' for row in tab for c in row):
            errors.append(f'{tab.title}: formula error cells')
        for i in range(1,min(tab.max_row,30)+1):
            idcols=[c.column for c in tab[i] if str(c.value or '').lower().replace(' ','') in {'视频id','达人id','creatorid','videoid'}]
            if idcols:
                for row in tab.iter_rows(min_row=i+1):
                    for col in idcols:
                        val=row[col-1].value
                        if isinstance(val,(int,float)) and abs(val)>=10**15:
                            errors.append(f'{tab.title}: long ID must remain text at {row[col-1].coordinate}')
                break
    book.close()
    return errors

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--results', type=Path, required=True)
    p.add_argument('--workbook', type=Path)
    p.add_argument('--allow-incomplete', action='store_true')
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    source = json.loads(args.input.read_text(encoding='utf-8'))
    result = json.loads(args.results.read_text(encoding='utf-8'))
    report = validate(source, result, args.allow_incomplete)
    if args.workbook:
        report['errors'].extend(check_workbook(args.workbook, source, result))
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report['errors']))

if __name__ == '__main__':
    main()
