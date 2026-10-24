import unittest
from datetime import date
from report_core import HEADER, LEGACY_HEADER, SchemaError, make_record, schema_upgrade, GoogleRepository

class FakeWorksheet:
    col_count = 13
    def __init__(self):
        self.rows = []
        self.raise_after_append = False
    def row_values(self, row):
        return self.rows[row-1][:] if len(self.rows) >= row else []
    def get_all_values(self):
        return self.rows
    def resize(self, cols):
        self.col_count = cols
    def update(self, range_name, values, value_input_option):
        if not self.rows: self.rows.append([])
        self.rows[0] = values[0][:]
    def col_values(self, col):
        return [r[col-1] if len(r) >= col else '' for r in self.rows]
    def append_row(self, values, **kwargs):
        self.rows.append(values[:])
        if self.raise_after_append:
            self.raise_after_append = False
            raise ConnectionError('response lost')

class FakeBook:
    def __init__(self, ws): self.ws = ws
    def worksheet(self, title): return self.ws

class ReportTests(unittest.TestCase):
    def setUp(self):
        self.common = dict(location='けやきプラザ', reporter='テスト担当', date=date(2026,10,22))
        self.data = dict(types=['パソコン','スマートフォン'], content='=1+1', result='説明した')
        self.record = make_record(self.common, self.data, 'same-report-id')
    def test_empty_optional_columns_are_preserved(self):
        row = [self.record[h] for h in HEADER]
        self.assertEqual(row[6:8], ['', ''])
        self.assertEqual(row[8:10], ['=1+1','説明した'])
        self.assertEqual(len(row),13)
    def test_validation(self):
        with self.assertRaises(ValueError): make_record(self.common, {}, 'x')
    def test_schema_safety(self):
        self.assertEqual(schema_upgrade([]), HEADER)
        self.assertEqual(schema_upgrade(LEGACY_HEADER), HEADER)
        with self.assertRaises(SchemaError): schema_upgrade(['日付','内容'])
        with self.assertRaises(SchemaError): schema_upgrade([], True)
    def repo(self,ws):
        r=GoogleRepository.__new__(GoogleRepository); r.book=FakeBook(ws)
        return r
    def test_first_save_with_blanks(self):
        ws=FakeWorksheet(); self.repo(ws).save(self.record)
        self.assertEqual(ws.rows[0], HEADER)
        self.assertEqual(ws.rows[1][6:8], ['', ''])
        self.assertEqual(ws.rows[1][8], '=1+1')
    def test_first_save_with_padded_empty_response(self):
        class PaddedWorksheet(FakeWorksheet):
            def get_all_values(self):
                return self.rows or [[''] * len(HEADER) for _ in range(100)]
        ws=PaddedWorksheet()
        self.repo(ws).save(self.record)
        self.assertEqual(ws.rows[0], HEADER)
        self.assertEqual(ws.rows[1][8], '=1+1')
    def test_retry_after_lost_response_not_duplicated(self):
        ws=FakeWorksheet(); ws.raise_after_append=True; r=self.repo(ws)
        with self.assertRaises(ConnectionError): r.save(self.record)
        self.assertEqual(r.save(self.record),'already_saved')
        self.assertEqual(len(ws.rows),2)
    def test_old_rows_untouched_on_extension(self):
        ws=FakeWorksheet(); old=['old']*10; ws.rows=[LEGACY_HEADER[:], old[:]]
        self.repo(ws).save(self.record)
        self.assertEqual(ws.rows[1], old)
    def test_unknown_header_is_not_modified(self):
        ws=FakeWorksheet(); ws.rows=[['日付','内容'],['old','data']]
        with self.assertRaises(SchemaError): self.repo(ws).save(self.record)
        self.assertEqual(ws.rows,[['日付','内容'],['old','data']])

if __name__ == '__main__': unittest.main()
