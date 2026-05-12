import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. 認証設定
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# 2. 定数設定
LOCATIONS = ["けやきプラザ", "新木近隣センター", "並木近隣センター"]
# 予約された9項目の定義
HEADER = ["保存日時", "拠点", "報告者", "開催日", "認知経路", "相談種別", "来場者名", "助言者", "相談内容", "結果"]

st.title("ぱそすまサロン 活動報告")

# 3. メインフォームの構築
with st.form("main_form"):
    loc = st.selectbox("開催場所", LOCATIONS)
    reporter = st.text_input("報告者名")
    date = st.date_input("開催日", datetime.now())

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
    content = st.text_area("相談内容")
    result = st.text_area("対応結果・備考")
    
    if st.form_submit_button("報告書を送信"):
        # 相談種別を結合
        selected_types = []
        if type_pc: selected_types.append("パソコン")
        if type_sp: selected_types.append("スマートフォン")
        if type_etc: selected_types.append("その他")
        types_str = " / ".join(selected_types)

        sheet_title = f"{date.strftime('%Y-%m')}_{loc}"
        spreadsheet = client.open("ぱそすまサロン報告書")
        
        try:
            worksheet = spreadsheet.worksheet(sheet_title)
            # 既存シートの見出しが古い（列が少ない）場合、最新の9項目で上書きする
            existing_header = worksheet.row_values(1)
            if len(existing_header) < len(HEADER):
                worksheet.update('A1', [HEADER])
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_title, rows=100, cols=len(HEADER))
            worksheet.append_row(HEADER)
        
        # 保存するデータの作成（順番をHEADERと完全に一致させる）
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = [
            timestamp,     # 1: 保存日時
            loc,           # 2: 拠点
            reporter,      # 3: 報告者
            str(date),     # 4: 開催日
            know_from,     # 5: 認知経路
            types_str,     # 6: 相談種別
            visitor_name,  # 7: 来場者名
            advisor_name,  # 8: 助言者
            content,       # 9: 相談内容
            result         # 10: 結果
        ]
        
        worksheet.append_row(new_row)
        st.success(f"データを保存しました。")