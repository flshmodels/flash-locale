"""Check Roblox-style localization CSV files without uploading or changing them."""
import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path
import re
import sys

MAX_BYTES = 2 * 1024 * 1024
FORMATS = {'int', 'fixed', 'num', 'HEX', 'hex', 'datetime', 'iso8601', 'shorttime', 'shortdatetime', 'shortdate', 'translate'}
TOKEN = re.compile(r'([A-Za-z_][A-Za-z0-9_]*|[1-9][0-9]*)(?::([A-Za-z0-9_]+))?\Z')
LOCALE = re.compile(r'[a-z]{2,3}(?:-[a-z0-9]{2,8})*\Z')


class CatalogError(ValueError):
    pass


def placeholders(text):
    tokens = Counter()
    kinds = set()
    for match in re.finditer(r'\{([^{}]*)\}|[{}]', text):
        if match.group(1) is None:
            raise CatalogError('Unmatched or nested brace; literal braces are not supported by this checker.')
        token = TOKEN.fullmatch(match.group(1))
        if not token:
            raise CatalogError('Unsupported placeholder syntax: ' + match.group(0))
        name, specifier = token.groups()
        if specifier and specifier not in FORMATS:
            raise CatalogError('Unsupported format specifier: ' + specifier)
        kinds.add(name.isdigit())
        tokens[(name, specifier or '')] += 1
    if len(kinds) > 1:
        raise CatalogError('Use either numbered or named parameters within one string, not both.')
    return tokens


def load_csv(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise CatalogError('Input exceeds 2 MiB.')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
    headers = reader.fieldnames
    if not headers or 'Source' not in headers or len(headers) != len(set(headers)):
        raise CatalogError('CSV needs a Source column and distinct headers.')
    metadata = {'Key', 'Context', 'Example', 'Source'}
    locales = [header for header in headers if header not in metadata]
    if not 1 <= len(locales) <= 32 or any(not LOCALE.fullmatch(locale) for locale in locales):
        raise CatalogError('Use 1-32 lowercase locale columns, such as es or pt-br. Other columns may be Key, Context and Example.')
    rows = []
    for index, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise CatalogError(f'Record {index}: wrong number of columns.')
        if len(rows) >= 10000:
            raise CatalogError('Input exceeds 10000 records.')
        rows.append(row)
    if not rows:
        raise CatalogError('CSV contains no entries.')
    return locales, rows


def check(locales, rows, required=()):
    if set(required) - set(locales):
        raise CatalogError('Required locales must already have columns in the CSV.')
    coverage = {locale: 0 for locale in locales}
    issues, total = [], 0
    keys, unkeyed = set(), set()

    def issue(row, column, code, message):
        nonlocal total
        total += 1
        if len(issues) < 200:
            issues.append({'record': row, 'column': column, 'code': code, 'message': message})

    for number, row in enumerate(rows, 2):
        source = row['Source']
        key, context = row.get('Key', ''), row.get('Context', '')
        for column, value in row.items():
            limit = 128 if column == 'Key' else 1024 if column == 'Context' else 4096
            if len(value.encode('utf-8')) > limit:
                issue(number, column, 'text_too_long', f'Field exceeds {limit} UTF-8 bytes.')
        if not source.strip():
            issue(number, 'Source', 'missing_source', 'Source must contain non-whitespace text.')
        if key:
            if key in keys:
                issue(number, 'Key', 'duplicate_key', 'Keys must be unique under this checker\'s policy.')
            keys.add(key)
        else:
            identity = (source, context)
            if identity in unkeyed:
                issue(number, 'Source', 'duplicate_entry', 'Unkeyed Source/Context pair is repeated.')
            unkeyed.add(identity)
        source_tokens = None
        try:
            source_tokens = placeholders(source)
        except CatalogError as error:
            issue(number, 'Source', 'invalid_placeholder', str(error))
        for locale in locales:
            text = row[locale]
            if not text.strip():
                if locale in required:
                    issue(number, locale, 'missing_translation', 'Required translation is blank.')
                continue
            coverage[locale] += 1
            try:
                translated = placeholders(text)
                if source_tokens is not None and translated != source_tokens:
                    issue(number, locale, 'placeholder_mismatch', 'Placeholder names, formats and repetition counts must match Source.')
            except CatalogError as error:
                issue(number, locale, 'invalid_placeholder', str(error))
    return {'rows': len(rows), 'locales': locales, 'translated': coverage, 'issueCount': total, 'issues': issues, 'issuesTruncated': total > len(issues)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--require-locale', action='append', default=[], metavar='LOCALE')
    parser.add_argument('--json', action='store_true', help='print a JSON report instead of readable text')
    args = parser.parse_args(argv)
    try:
        locales, rows = load_csv(args.input)
        report = check(locales, rows, args.require_locale)
    except (OSError, ValueError, UnicodeError, csv.Error) as error:
        print('flash-locale: ' + str(error), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(f"{report['rows']} entries / {report['issueCount']} findings")
        for locale in report['locales']:
            print(f"  {locale}: {report['translated'][locale]}/{report['rows']} translations present")
        for item in report['issues']:
            print(f"  Record {item['record']} [{item['column']}] {item['code']}: {item['message']}")
        if report['issuesTruncated']:
            print('  Only the first 200 findings are shown.')
    return 1 if report['issueCount'] else 0


if __name__ == '__main__':
    sys.exit(main())
