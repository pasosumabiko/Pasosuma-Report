"""Data validation and Google Sheets persistence, independent of the screen."""
from datetime import datetime, timezone, timedelta
from threading import RLock

JST = timezone(timedelta(hours=9))
LOCATIONS = ['けやきプラザ', '新木近隣センター', '並木近隣センター']
LEGACY_HEADER = ['保存日時', '拠点', '報告者', '開催日', '認知経路', '相談種別', '来場者名', '助言者', '相談内容', '結果']
HEADER = LEGACY_HEADER + ['報告ID', '相談テーマ', '対応区分']
LOCK = RLock()

class SchemaError(ValueError):
    pass

def now_jst():
    return datetime.now(JST)

def validate(common, data):
    errors = []
    if common.get('location') not in LOCATIONS:
        errors.append('会場を選んでください。')
    if not common.get('reporter', '').strip():
        errors.append('担当サポーター名を入力してください。')
    if not common.get('date'):
        errors.append('開催日を選んでください。')
    if not data.get('types'):
        errors.append('相談種別を１つ以上選んでください。')
    if not data.get('content', '').strip():
        errors.append('相談内容を入力してください。')
    if not data.get('result', '').strip():
        errors.append('対応結果を入力してください（未解決の場合も状況を記入）。')
    return errors

def make_record(common, data, report_id):
    errors = validate(common, data)
    if errors:
        raise ValueError('\n'.join(errors))
    return dict(zip(HEADER, [
        now_jst().isoformat(timespec='seconds'), common['location'],
        common['reporter'].strip(), common['date'].isoformat(),
        data.get('known_from', '未確認'), ' / '.join(data['types']),
        data.get('visitor', '').strip(), data.get('advisor', '').strip(),
        data['content'].strip(), data['result'].strip(), report_id,
        data.get('topic', '未分類'), data.get('outcome', '未分類')
    ]))

def schema_upgrade(existing, has_other_rows=False):
    """Never relabel existing data. Allow only known, ordered prefix extensions."""
    if not existing:
        if has_other_rows:
            raise SchemaError('１行目が空欄ですが、下にデータがあります。管理者が見出しを確認してください。')
        return HEADER[:]
    if existing == HEADER:
        return existing[:]
    if len(existing) >= len(LEGACY_HEADER) and existing == HEADER[:len(existing)]:
        return HEADER[:]
    raise SchemaError('保存先の列見出しが想定と異なります。既存データ保護のため保存を止めました。管理者が列順を確認してください。')

class GoogleRepository:
    def __init__(self, credentials, spreadsheet_id):
        import gspread
        from google.oauth2.service_account import Credentials
        self.gspread = gspread
        creds = Credentials.from_service_account_info(
            credentials, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        self.book = gspread.authorize(creds).open_by_key(spreadsheet_id)

    def save(self, record):
        # This lock serializes check+append in this process. The test deployment
        # must use a dedicated spreadsheet and a single app process.
        with LOCK:
            title = record['開催日'][:7] + '_' + record['拠点']
            try:
                ws = self.book.worksheet(title)
            except self.gspread.exceptions.WorksheetNotFound:
                ws = self.book.add_worksheet(title=title, rows=100, cols=len(HEADER))
            existing = ws.row_values(1)
            target = schema_upgrade(existing, has_other_rows=bool(ws.get_all_values()) if not existing else False)
            if target != existing:
                # Exact old ten-column header is safe to extend; never overwrite
                # unknown legacy layouts, even if their column count is smaller.
                if ws.col_count < len(HEADER):
                    ws.resize(cols=len(HEADER))
                ws.update(range_name='A1:M1', values=[target], value_input_option='RAW')
            ids = ws.col_values(HEADER.index('報告ID') + 1)
            if record['報告ID'] in ids[1:]:
                return 'already_saved'
            # RAW keeps text such as =... as text; explicit range fixes the
            # starting column even when optional fields are empty.
            ws.append_row([record.get(h, '') for h in HEADER],
                          value_input_option='RAW', table_range='A1:M1')
            return 'saved'
