import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. 認証設定
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 2. 定数・リストの設定
LOCATIONS = ["けやきプラザ", "新木近隣センター", "並木近隣センター"]
# 最新のヘッダー定義（9項目）
HEADER = ["保存日時", "報告者", "開催日", "認知経路", "相談種別", "来場者名", "助言者", "相談内容", "結果"]

st.title("ぱそすまサロン 活動報告")

# サイドバー：メンテナンス機能
if st.sidebar.checkbox("メンテナンス（拠点管理）"):
    st.sidebar.subheader("拠点の追加・削除")

# 3. メインフォームの構築
with st.form("main_form"):
    loc = st.selectbox("開催場所", LOCATIONS)
    reporter = st.text_input("報告者名")
    date = st.date_input("開催日", datetime.now())

    # --- 追加項目 ---
    know_from = st.radio(
        "ぱそすまサロンをどこで知りましたか？",
        ["広報", "ポスター", "知人から", "その他"],
        horizontal=True
    )

    st.write("相談種別（複数選択可）")
    c1, c2, c3 = st.columns(3)
    with c1:
        type_pc = st.checkbox("パソコン")
    with c2:
        type_sp = st.checkbox("スマートフォン")
    with c3:
        type_etc = st.checkbox("その他")

    visitor_name = st.text_input("来場者名（許可を得た場合のみ）")
    advisor_name = st.text_input("助言者（助言を受けた場合）")
    # ----------------

    content = st.text_area("相談内容")
    result = st.text_area("対応結果・備考")
    
    # 送信ボタン
    if st.form_submit_button("報告書を送信"):
        # 相談種別のチェックをまとめる
        selected_types = []
        if type_pc: selected_types.append("パソコン")
        if type_sp: selected_types.append("スマートフォン")
        if type_etc: selected_types.append("その他")
        types_str = " / ".join(selected_types)

        # シート名を特定
        sheet_title = f"{date.strftime('%Y-%m')}_{loc}"
        spreadsheet = client.open("ぱそすまサロン報告書")
        
        try:
            worksheet = spreadsheet.worksheet(sheet_title)
            # 【論理チェック】シートが存在する場合、1行目の見出しが最新(9列)か確認
            existing_header = worksheet.row_values(1)
            if len(existing_header) < len(HEADER):
                # 古い形式の場合は、1行目を最新のヘッダーで上書き更新する
                worksheet.update('A1', [HEADER])
        except gspread.exceptions.WorksheetNotFound:
            # シートがない場合は新規作成
            worksheet = spreadsheet.add_worksheet(title=sheet_title, rows=100, cols=len(HEADER))
            worksheet.append_row(HEADER)
        
        # 4. データの書き込み
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = [
            timestamp, reporter, str(date), know_from, 
            types_str, visitor_name, advisor_name, content, result
        ]
        worksheet.append_row(new_row)
        
        st.success(f"シート「{sheet_title}」にデータを保存しました。")