# Flash Locale

Check a Roblox-style localization CSV before importing it. Find blank required translations, duplicate keys and mismatched placeholders without translating, uploading or modifying the file.

## Run it

Python 3.11+; no packages to install:

```sh
python flash_locale.py examples/strings.csv
python flash_locale.py examples/strings.csv --require-locale es --require-locale fr --json
python -m unittest discover -s tests -v
```

The report prints coverage and up to 200 findings, while retaining the complete finding count. `--json` prints a machine-readable report to stdout. Exit 0 means this check passed, 1 means lint findings, and 2 means input/file/usage failure. Redirect stdout if you want to save a report. The input file is never changed.

## CSV format

`Source` is required. `Key`, `Context` and `Example` are optional. Other headers are 1–32 lowercase locale identifiers such as `es` or `pt-br`. UTF-8 BOMs and quoted multiline fields are accepted. Header names and entries are case-sensitive.

Blank translations are included in coverage but are not failures unless their locale is named with `--require-locale`. Required locales must already have CSV columns. Empty or whitespace-only Source values are findings.

The checker requires globally distinct nonempty Keys. Unkeyed entries must have distinct Source/Context pairs. These are lint policies, not a complete model of Roblox's cloud import behavior. Keyed entries may share source text. Locale headers are syntax-checked, not checked against Roblox's current supported-language list.

## Placeholders

Named parameters such as `{name}` and numbered parameters such as `{1:int}` are supported. Within one string, use names or numbers, not both. Translations must preserve parameter names, specifiers and repetition counts; reordering is allowed. The checker does not judge translation meaning or grammar.

Supported specifiers: int, fixed, num, HEX, hex, datetime, iso8601, shorttime, shortdatetime, shortdate, translate. Literal braces, nested braces and other placeholder formats are rejected by this version. A deliberate translation that changes repetition may need a different source structure or a revised lint policy.

## Limits and code

Input: 2 MiB and 10000 records. Field limits in UTF-8 bytes: Key 128, Context 1024, other fields 4096. Record numbers identify logical CSV records, not necessarily physical lines when fields contain newlines.

`load_csv(path)` returns locale names and rows. `placeholders(text)` returns a counted set of name/specifier pairs. `check(locales, rows, required)` returns coverage, total issues and a capped issue list. Structural CSV errors stop processing. The CLI does not execute formulas, render rich text, validate asset permissions, access Roblox accounts or call any service.

CI tests the parser, placeholder policies, limits, unchanged inputs and exit codes on Windows and Linux. It does not verify a live cloud-table import. See [references](docs/REFERENCES.md).

MIT licensed. See [LICENSE](LICENSE).
