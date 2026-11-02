from pathlib import Path
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flash_locale as locale


class LocaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def file(self, text):
        path = Path(self.temp.name) / 'strings.csv'
        path.write_text(text, encoding='utf-8', newline='')
        return path

    def test_bom_quotes_and_multiline_fields(self):
        path = self.file('\ufeffKey,Context,Source,es\nhello,HUD,"Hello, {name}\nagain","Hola, {name}\notra vez"\n')
        locales, rows = locale.load_csv(path)
        self.assertEqual(locale.check(locales, rows)['issueCount'], 0)

    def test_placeholder_names_formats_and_counts(self):
        base = {'Source': '{coins:int} {coins:int}', 'es': '{coins:int}'}
        self.assertEqual(locale.check(['es'], [base])['issues'][0]['code'], 'placeholder_mismatch')
        for target in ('{coin:int} {coin:int}', '{coins:num} {coins:num}', ''):
            report = locale.check(['es'], [{'Source': '{coins:int} {coins:int}', 'es': target}], ['es'])
            self.assertGreater(report['issueCount'], 0)

    def test_named_numbered_and_supported_formats(self):
        self.assertEqual(len(locale.placeholders('{1:num} {2:int}')), 2)
        for specifier in locale.FORMATS:
            self.assertEqual(sum(locale.placeholders('{value:' + specifier + '}').values()), 1)
        for text in ('{name} {1}', '{name:unknown}', '{a b}', '{0}', '{{name}}', '{name', 'name}'):
            with self.subTest(text=text), self.assertRaises(locale.CatalogError):
                locale.placeholders(text)

    def test_required_translations_and_optional_coverage(self):
        rows = [{'Source': 'Hello', 'es': '', 'fr': 'Bonjour'}]
        report = locale.check(['es', 'fr'], rows)
        self.assertEqual(report['issueCount'], 0)
        self.assertEqual(report['translated'], {'es': 0, 'fr': 1})
        self.assertEqual(locale.check(['es', 'fr'], rows, ['es'])['issueCount'], 1)
        with self.assertRaises(locale.CatalogError):
            locale.check(['es'], [{'Source': 'Hi', 'es': 'Hola'}], ['fr'])

    def test_duplicate_keys_and_unkeyed_contexts(self):
        rows = [{'Key': 'a', 'Source': 'One', 'es': 'Uno'}, {'Key': 'a', 'Source': 'Two', 'es': 'Dos'}]
        self.assertEqual(locale.check(['es'], rows)['issues'][0]['code'], 'duplicate_key')
        rows = [{'Source': 'Back', 'Context': 'Menu', 'es': 'Volver'}] * 2
        self.assertEqual(locale.check(['es'], rows)['issueCount'], 1)
        rows[1] = {'Source': 'Back', 'Context': 'Body', 'es': 'Espalda'}
        self.assertEqual(locale.check(['es'], rows)['issueCount'], 0)

    def test_malformed_headers_and_record_shapes(self):
        for text in ('Source,es,es\nA,B,C\n', 'Key,es\na,b\n', 'Source,ES\nA,B\n', 'Source,es\nA\n', 'Source,es\n', 'Source,es\n"unterminated,B'):
            with self.subTest(text=text), self.assertRaises((locale.CatalogError, csv.Error)):
                locale.load_csv(self.file(text))

    def test_file_and_record_limits(self):
        with self.assertRaises(locale.CatalogError):
            locale.load_csv(self.file('x' * (locale.MAX_BYTES + 1)))
        with self.assertRaises(locale.CatalogError):
            locale.load_csv(self.file('Source,es\n' + 'A,B\n' * 10001))

    def test_text_limits_and_issue_truncation(self):
        rows = [{'Source': 'A', 'es': '{missing}'}] * 250
        report = locale.check(['es'], rows)
        self.assertGreater(report['issueCount'], 200)
        self.assertEqual(len(report['issues']), 200)
        self.assertTrue(report['issuesTruncated'])
        self.assertTrue(locale.check(['es'], [{'Key': 'x' * 129, 'Source': 'A', 'es': 'B'}])['issueCount'])

    def test_cli_exit_codes_and_input_unchanged(self):
        path = self.file('Source,es\nHello,Hola\n')
        original = path.read_bytes()
        command = [sys.executable, str(Path(locale.__file__)), str(path), '--json']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['rows'], 1)
        self.assertEqual(path.read_bytes(), original)
        self.file('Source,es\nHello {name},Hola\n')
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        self.file('Source,es,es\nA,B,C\n')
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)

    def test_whitespace_source_is_invalid(self):
        self.assertEqual(locale.check(['es'], [{'Source': ' ', 'es': 'A'}])['issues'][0]['code'], 'missing_source')


if __name__ == '__main__':
    unittest.main()
