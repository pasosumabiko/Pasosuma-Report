import os
import hmac
from uuid import uuid4
import streamlit as st
from report_core import LOCATIONS, HEADER, GoogleRepository, make_record, now_jst

st.set_page_config(page_title='ぱそすまサロン｜報告テスト', page_icon='📝', layout='centered')
if st.session_state.pop('_reset_simulation_next_run', False):
    st.session_state.simulate_failure = False

def setting(name, default=None):
    try:
        return st.secrets.get(name, default)
    except FileNotFoundError:
        return default

# Safety default: no Google connection unless explicitly enabled in Secrets.
MODE = os.environ.get('PASOSUMA_MODE', setting('mode', 'demo'))
if MODE not in ('demo', 'google_test'):
    st.error('保存モードの設定を確認してください。')
    st.stop()

st.title('ぱそすまサロン 活動報告')
if MODE == 'demo':
    st.info('お試し版：Googleには送信しません。架空の相談で操作を確認してください。')
else:
    st.warning('テスト運用：テスト専用のGoogleスプレッドシートへ保存します。')
    pin = str(setting('access_code', ''))
    if not pin or not setting('spreadsheet_id') or not setting('gcp_service_account'):
        st.error('管理者がテスト用の保存先・認証情報・利用コードを設定してください。')
        st.stop()
    if not st.session_state.get('authorized'):
        with st.form('login'):
            code = st.text_input('利用コード', type='password')
            login = st.form_submit_button('利用する')
        if login:
            if hmac.compare_digest(code.encode('utf-8'), pin.encode('utf-8')):
                st.session_state.authorized = True
                st.rerun()
            else:
                st.error('利用コードを確認してください。')
        st.stop()

DEFAULTS = {'q_known': '未確認', 'q_pc': False, 'q_sp': False, 'q_other': False,
            'q_visitor': '', 'q_advisor': '', 'q_content': '', 'q_result': '',
            'q_topic': '未分類', 'q_outcome': '未分類'}
if st.session_state.pop('_reset_consultation', False):
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
st.session_state.setdefault('saved_count', 0)
st.session_state.setdefault('demo_rows', [])
pending = st.session_state.get('pending_record')
common = st.session_state.get('common')
if pending:
    # Restore from the frozen request before rendering disabled form widgets.
    # This also avoids stale form values after an immediate rerun on failure.
    for key, column in [('q_content','相談内容'), ('q_result','結果'),
                        ('q_known','認知経路'), ('q_visitor','来場者名'),
                        ('q_advisor','助言者'), ('q_topic','相談テーマ'), ('q_outcome','対応区分')]:
        st.session_state[key] = pending[column]
    for key, label in [('q_pc','パソコン'), ('q_sp','スマートフォン'), ('q_other','その他')]:
        st.session_state[key] = label in pending['相談種別'].split(' / ')

st.subheader('１　今回の開催情報')
if common:
    st.success(f"{common['date']:%Y年%m月%d日} ／ {common['location']} ／ 担当サポーター：{common['reporter']}")
    st.caption('このスマホでご自身が担当した相談を続けて報告できます。開催情報と担当サポーター名を引き継ぎます。')
with st.expander('開催情報を変更する' if common else '最初に開催情報を設定してください', expanded=not bool(common)):
    with st.form('event_form'):
        loc = st.selectbox('会場', LOCATIONS, index=LOCATIONS.index(common['location']) if common else None,
                           placeholder='会場を選択', disabled=bool(pending))
        reporter = st.text_input('担当サポーター名', value=common['reporter'] if common else '', disabled=bool(pending),
                                 help='このスマホを使うサポーターご本人の名前を入力してください。ご自身が担当した相談を報告します。')
        event_date = st.date_input('開催日', value=common['date'] if common else now_jst().date(),
                                   format='YYYY/MM/DD', disabled=bool(pending))
        apply = st.form_submit_button('この開催情報で入力する', disabled=bool(pending))
    if apply:
        if not loc or not reporter.strip() or not event_date:
            st.error('会場・担当サポーター名・開催日を設定してください。')
        else:
            st.session_state.common = {'location': loc, 'reporter': reporter.strip(), 'date': event_date}
            st.rerun()
if not common:
    st.stop()

receipt = st.session_state.get('receipt')
if receipt:
    st.success(f"保存できました（受付番号：{receipt[:8]}）。相談欄を空にしました。次の相談を入力できます。")
st.caption(f"この画面で保存した件数：{st.session_state.saved_count}件")
st.subheader('２　相談１件の報告')
st.caption('＊は必須です。来場者名・助言者名は空欄のままで構いません。')
if MODE == 'demo':
    st.checkbox('テスト用：次の保存時に通信エラーを再現する（保存後に応答が途切れた場合）', key='simulate_failure')

with st.form('consultation_form', clear_on_submit=False):
    disabled = bool(pending)
    st.radio('知ったきっかけ', ['未確認', '広報', 'ポスター', '知人から', 'その他'],
             horizontal=True, key='q_known', disabled=disabled)
    st.write('相談種別＊（複数選択可）')
    cols = st.columns(3)
    for col, label, key in zip(cols, ['パソコン', 'スマートフォン', 'その他'], ['q_pc', 'q_sp', 'q_other']):
        col.checkbox(label, key=key, disabled=disabled)
    st.selectbox('相談テーマ（任意）', ['未分類', '操作方法', '設定', 'アプリ', '不具合', 'その他'], key='q_topic', disabled=disabled)
    st.text_area('相談内容＊', placeholder='例：写真を家族に送りたい', key='q_content', disabled=disabled)
    st.selectbox('対応区分（任意）', ['未分類', '説明・練習', '設定変更', '調査・確認', '継続対応', 'その他'], key='q_outcome', disabled=disabled)
    st.text_area('対応結果・備考＊', placeholder='例：写真の送信方法を説明し、一緒に練習した', key='q_result', disabled=disabled)
    with st.expander('氏名を記録する場合のみ開く（任意）'):
        st.text_input('来場者名（本人の許可を得た場合のみ）', key='q_visitor', disabled=disabled)
        st.text_input('助言者名（助言を受けた場合のみ）', key='q_advisor', disabled=disabled)
    submitted = st.form_submit_button('この相談を保存する', type='primary', disabled=disabled)

def save_pending():
    record = st.session_state.pending_record
    try:
        if MODE == 'demo':
            if not any(r['報告ID'] == record['報告ID'] for r in st.session_state.demo_rows):
                st.session_state.demo_rows.append(record.copy())
            if st.session_state.get('simulate_failure'):
                st.session_state['_reset_simulation_next_run'] = True
                raise ConnectionError('simulated timeout after save')
        else:
            GoogleRepository(dict(setting('gcp_service_account')), setting('spreadsheet_id')).save(record)
    except Exception as exc:
        # Do not display credentials, user data or raw provider response bodies.
        from report_core import SchemaError
        st.session_state.save_error = str(exc) if isinstance(exc, SchemaError) else '保存完了を確認できませんでした。入力は残しています。同じ受付番号で確認・再試行してください。'
        return False
    st.session_state.receipt = record['報告ID']
    st.session_state.saved_count += 1
    st.session_state.pop('pending_record', None)
    st.session_state.pop('save_error', None)
    st.session_state['_reset_consultation'] = True
    return True

if submitted:
    data = {'known_from': st.session_state.q_known,
            'types': [label for label, key in [('パソコン', 'q_pc'), ('スマートフォン', 'q_sp'), ('その他', 'q_other')] if st.session_state[key]],
            'content': st.session_state.q_content, 'result': st.session_state.q_result,
            'visitor': st.session_state.q_visitor, 'advisor': st.session_state.q_advisor,
            'topic': st.session_state.q_topic, 'outcome': st.session_state.q_outcome}
    try:
        st.session_state.pending_record = make_record(common, data, str(uuid4()))
        st.session_state.pop('receipt', None)
    except ValueError as exc:
        st.error(str(exc))
    else:
        with st.spinner('保存を確認しています…'):
            save_pending()
        st.rerun()

if st.session_state.get('pending_record'):
    st.error(st.session_state.get('save_error', '保存確認が必要です。'))
    st.caption('確認が済むまで、この報告の内容を保持します。画面を閉じずに再試行してください。')
    if st.button('保存結果を確認・再試行する', type='primary'):
        with st.spinner('同じ報告の保存状況を確認しています…'):
            save_pending()
        st.rerun()

if MODE == 'demo':
    with st.expander('テストで保存した内容を見る'):
        st.dataframe(st.session_state.demo_rows, hide_index=True)
st.caption('開催情報と入力途中の内容はこの接続中に保持されます。再読み込み・接続切断後の復元は対象外です。')
