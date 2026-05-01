import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. 認証設定
# Google Cloud Consoleで取得したJSONファイルへのパスを指定します
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
#creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
# 修正後のコード（あきらさんのフォルダ構成に合わせました）
# クラウド公開用（Secretsを使用）
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 2. 拠点リスト（メンテナンス機能の基礎）
# 将来的にはマスタシートから読み込むように拡張可能です
LOCATIONS = ["けやきプラザ", "新木近隣センター", "並木近隣センター"]

st.title("ぱそすまサロン 活動報告")

# サイドバー：メンテナンス機能（拠点の管理用）
if st.sidebar.checkbox("メンテナンス（拠点管理）"):
    st.sidebar.subheader("拠点の追加・削除")
    # ここにマスタシートを読み書きするロジックを追記することで動的な管理が可能です

# 3. メインフォームの構築
with st.form("main_form"):
    loc = st.selectbox("開催場所", LOCATIONS)
    reporter = st.text_input("報告者名")
    date = st.date_input("開催日", datetime.now())
    content = st.text_area("相談内容")
    result = st.text_area("対応結果・備考")
    
    # 送信ボタンが押された時の処理
    if st.form_submit_button("報告書を送信"):
        # 月別・場所別のシート名を動的に特定（例: 2026-05_けやきプラザ）
        sheet_title = f"{date.strftime('%Y-%m')}_{loc}"
        
        # あらかじめ作成したスプレッドシートを開く
        spreadsheet = client.open("ぱそすまサロン報告書")
        
        try:
            # 既存のシートを探す
            worksheet = spreadsheet.worksheet(sheet_title)
        except gspread.exceptions.WorksheetNotFound:
            # シートが存在しない場合は、月別・場所別の新しいシートを自動作成
            worksheet = spreadsheet.add_worksheet(title=sheet_title, rows=100, cols=10)
            # ヘッダー（項目名）を一行目に書き込む[cite: 1, 2]
            worksheet.append_row(["保存日時", "報告者", "開催日", "相談内容", "結果"])
        
        # 4. データの書き込み
        # 時刻はシステム側で自動取得するため、入力の手間がありません[cite: 1, 2]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([timestamp, reporter, str(date), content, result])
        
        st.success(f"シート「{sheet_title}」に報告書を保存しました。")
