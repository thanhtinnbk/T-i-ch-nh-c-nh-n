import datetime
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client, Client

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Sổ Thu Chi Gia Đình",
    page_icon="📗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- 2. CUSTOM CSS GIAO DIỆN MISA ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4f6f8;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    .misa-header {
        background: linear-gradient(135deg, #107c41 0%, #0b5a2f 100%);
        padding: 20px 30px;
        border-radius: 16px;
        color: white;
        box-shadow: 0 4px 20px rgba(16, 124, 65, 0.25);
        margin-bottom: 25px;
    }
    .misa-header h2 { color: white !important; margin: 0; font-weight: 700; }
    .misa-header p { color: #e0f2fe; margin: 5px 0 0 0; font-size: 14px; }

    .misa-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        margin-bottom: 10px;
    }
    .misa-card-income { border-left: 5px solid #2e7d32; }
    .misa-card-expense { border-left: 5px solid #c62828; }
    .misa-card-balance { border-left: 5px solid #1565c0; }
    .misa-card-asset { border-left: 5px solid #f57c00; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background-color: #ffffff; padding: 6px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 16px; font-weight: 600; color: #5f6368; }
    .stTabs [aria-selected="true"] { background-color: #e8f5e9 !important; color: #107c41 !important; }

    [data-testid="stForm"] {
        background: #ffffff; border-radius: 16px; padding: 20px; border: 1px solid #e0e0e0; box-shadow: 0 4px 16px rgba(0,0,0,0.03);
    }

    .stButton>button {
        background: #107c41 !important; color: white !important; font-weight: 600 !important; border-radius: 10px !important; border: none !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 3. KẾT NỐI SUPABASE ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")


def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


try:
    supabase = get_supabase_client()
except Exception:
    st.error("Chưa kết nối được Supabase.")
    st.stop()


# --- 4. HÀM DỮ LIỆU ---
def format_vnd(amount):
    return f"{amount:,.0f} đ".replace(",", ".")


def get_categories():
    try:
        res = supabase.table("categories").select("*").execute()
        df = pd.DataFrame(res.data)
        return df if not df.empty else pd.DataFrame(columns=["id", "name", "type"])
    except Exception:
        return pd.DataFrame(columns=["id", "name", "type"])


def get_transactions(year=None, month=None):
    try:
        res = supabase.table("transactions").select("*, categories(name, type)").execute()
        df = pd.DataFrame(res.data)
        if not df.empty and "categories" in df.columns:
            df["transaction_date"] = pd.to_datetime(df["transaction_date"])
            df["category_name"] = df["categories"].apply(lambda x: x["name"] if isinstance(x, dict) else "")
            df["type"] = df["categories"].apply(lambda x: x["type"] if isinstance(x, dict) else "")
            if year:
                df = df[df["transaction_date"].dt.year == year]
            if month:
                df = df[df["transaction_date"].dt.month == month]
        else:
            return pd.DataFrame(
                columns=["id", "transaction_date", "amount", "note", "category_id", "category_name", "type"]
            )
        return df
    except Exception:
        return pd.DataFrame(
            columns=["id", "transaction_date", "amount", "note", "category_id", "category_name", "type"]
        )


def get_budgets(year):
    try:
        res = supabase.table("annual_budgets").select("*, categories(name, type)").eq("year", year).execute()
        df = pd.DataFrame(res.data)
        if not df.empty and "categories" in df.columns:
            df["category_name"] = df["categories"].apply(lambda x: x["name"] if isinstance(x, dict) else "")
            df["type"] = df["categories"].apply(lambda x: x["type"] if isinstance(x, dict) else "")
            if "monthly_amount" not in df.columns:
                df["monthly_amount"] = df["planned_amount"] / 12
        else:
            return pd.DataFrame(
                columns=["id", "year", "category_id", "planned_amount", "monthly_amount", "category_name", "type"]
            )
        return df
    except Exception:
        return pd.DataFrame(
            columns=["id", "year", "category_id", "planned_amount", "monthly_amount", "category_name", "type"]
        )


def get_accounts():
    try:
        res = supabase.table("accounts").select("*").execute()
        df = pd.DataFrame(res.data)
        return df if not df.empty else pd.DataFrame(columns=["id", "name", "balance", "note"])
    except Exception:
        return pd.DataFrame(columns=["id", "name", "balance", "note"])


# --- 5. HEADER ---
st.markdown(
    """
    <div class="misa-header">
        <h2>📗 SỔ THU CHI & QUẢN LÝ TÀI CHÍNH</h2>
        <p>Quản lý tài sản, thu chi & kế hoạch tài chính gia đình toàn diện</p>
    </div>
""",
    unsafe_allow_html=True,
)

categories_df = get_categories()

tabs = st.tabs(
    [
        "📊 Tổng Quan & Báo Cáo",
        "💵 Tình Hình Tài Chính",
        "➕ Ghi Thu Chi",
        "🎯 Dự Kiến Hàng Tháng / Năm",
        "🛠️ Điều Chỉnh / Xóa",
        "⚙️ Danh Mục",
    ]
)

# ---------------------------------------------------------
# TAB 1: TỔNG QUAN & BÁO CÁO (CÓ XUẤT FILE EXCEL / CSV)
# ---------------------------------------------------------
with tabs[0]:
    c_filter1, c_filter2 = st.columns([1, 1])
    with c_filter1:
        rep_year = st.number_input(
            "Năm báo cáo", min_value=2020, max_value=2035, value=datetime.date.today().year, key="misa_y"
        )
    with c_filter2:
        rep_month = st.selectbox("Tháng báo cáo", list(range(1, 13)), index=datetime.date.today().month - 1)

    df_month = get_transactions(year=rep_year, month=rep_month)
    acc_df = get_accounts()
    total_assets = acc_df["balance"].sum() if not acc_df.empty else 0

    total_income = 0
    total_expense = 0
    balance = 0

    if not df_month.empty and "type" in df_month.columns:
        total_income = df_month[df_month["type"] == "Thu nhập"]["amount"].sum()
        total_expense = df_month[df_month["type"] == "Chi tiêu"]["amount"].sum()
        balance = total_income - total_expense

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(
            f'<div class="misa-card misa-card-asset"><span style="color:#5f6368; font-size:12px; font-weight:600;">TỔNG TÀI SẢN HIỆN CÓ</span><h3 style="color:#f57c00; margin:5px 0 0 0; font-weight:700;">{format_vnd(total_assets)}</h3></div>',
            unsafe_allow_html=True,
        )
    with col_m2:
        st.markdown(
            f'<div class="misa-card misa-card-income"><span style="color:#5f6368; font-size:12px; font-weight:600;">THU NHẬP THÁNG</span><h3 style="color:#2e7d32; margin:5px 0 0 0; font-weight:700;">{format_vnd(total_income)}</h3></div>',
            unsafe_allow_html=True,
        )
    with col_m3:
        st.markdown(
            f'<div class="misa-card misa-card-expense"><span style="color:#5f6368; font-size:12px; font-weight:600;">CHI TIÊU THÁNG</span><h3 style="color:#c62828; margin:5px 0 0 0; font-weight:700;">{format_vnd(total_expense)}</h3></div>',
            unsafe_allow_html=True,
        )
    with col_m4:
        st.markdown(
            f'<div class="misa-card misa-card-balance"><span style="color:#5f6368; font-size:12px; font-weight:600;">DƯ TRONG THÁNG</span><h3 style="color:#1565c0; margin:5px 0 0 0; font-weight:700;">{format_vnd(balance)}</h3></div>',
            unsafe_allow_html=True,
        )

    st.write("")

    if not df_month.empty and "type" in df_month.columns:
        col_g1, col_g2 = st.columns([1, 1])
        with col_g1:
            st.markdown("##### 🍩 Cơ cấu chi tiêu")
            expense_df = df_month[df_month["type"] == "Chi tiêu"]
            if not expense_df.empty:
                fig_pie = px.pie(
                    expense_df,
                    values="amount",
                    names="category_name",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Bold,
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Chưa có khoản chi tiêu trong tháng.")

        with col_g2:
            st.markdown("##### 📈 Thu chi theo ngày")
            daily_df = (
                df_month.groupby([df_month["transaction_date"].dt.day, "type"])["amount"].sum().unstack().fillna(0)
            )
            fig_bar = go.Figure()
            if "Thu nhập" in daily_df.columns:
                fig_bar.add_trace(go.Bar(x=daily_df.index, y=daily_df["Thu nhập"], name="Thu nhập", marker_color="#2e7d32"))
            if "Chi tiêu" in daily_df.columns:
                fig_bar.add_trace(go.Bar(x=daily_df.index, y=daily_df["Chi tiêu"], name="Chi tiêu", marker_color="#c62828"))
            fig_bar.update_layout(barmode="group", margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_bar, use_container_width=True)

        # HÀNG HIỂN THỊ LỊCH SỬ & NÚT XUẤT FILE
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            st.markdown("##### 📜 Sổ nhật ký giao dịch tháng này")
        with col_t2:
            # Tạo dữ liệu xuất file CSV / Excel
            export_df = df_month[["transaction_date", "type", "category_name", "amount", "note"]].sort_values(
                by="transaction_date", ascending=False
            )
            export_df.columns = ["Ngày Giao Dịch", "Loại", "Danh Mục", "Số Tiền (VNĐ)", "Ghi Chú"]

            # Chuyển đổi thành CSV với font UTF-8 hỗ trợ tiếng Việt
            csv_data = export_df.to_csv(index=False, encoding="utf-8-sig")

            st.download_button(
                label="📥 Xuất Dữ Liệu Ra File CSV / Excel",
                data=csv_data,
                file_name=f"Bao_Cao_Thu_Chi_Thang_{rep_month}_{rep_year}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        display_df = export_df.copy()
        display_df["Số Tiền (VNĐ)"] = display_df["Số Tiền (VNĐ)"].apply(format_vnd)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# TAB 2: TÌNH HÌNH TÀI CHÍNH
# ---------------------------------------------------------
with tabs[1]:
    st.subheader("💵 Quản Lý Tình Hình Tài Chính / Số Dư Hiện Có")
    acc_df = get_accounts()
    col_acc1, col_acc2 = st.columns([1, 1])

    with col_acc1:
        st.markdown("##### ➕ Thêm Ví / Tài Khoản Dự Trữ Mới")
        with st.form("add_acc_form", clear_on_submit=True):
            acc_name = st.text_input("Tên tài khoản / Ví", placeholder="Ví dụ: Tiền mặt, Vietcombank, Quỹ Tiết kiệm...")
            acc_balance = st.number_input("Số dư hiện tại (VNĐ)", min_value=0.0, step=500000.0, format="%.0f")
            acc_note = st.text_input("Ghi chú", placeholder="Ví dụ: Tài khoản chi tiêu chính...")

            if st.form_submit_button("➕ Thêm Tài Khoản", use_container_width=True):
                if acc_name.strip():
                    supabase.table("accounts").insert(
                        {"name": acc_name.strip(), "balance": acc_balance, "note": acc_note}
                    ).execute()
                    st.success("Đã thêm tài khoản thành công!")
                    st.rerun()

    with col_acc2:
        st.markdown("##### 📋 Cập Nhật Số Dư Trực Tiếp")
        if not acc_df.empty:
            for _, row in acc_df.iterrows():
                with st.expander(f"🏦 {row['name']} - **{format_vnd(row['balance'])}**"):
                    with st.form(f"edit_acc_{row['id']}"):
                        new_bal = st.number_input(
                            "Số dư mới (VNĐ)", min_value=0.0, value=float(row["balance"]), step=100000.0, format="%.0f"
                        )
                        new_acc_note = st.text_input("Ghi chú", value=str(row["note"] if row["note"] else ""))
                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            if st.form_submit_button("💾 Cập nhật", use_container_width=True):
                                supabase.table("accounts").update({"balance": new_bal, "note": new_acc_note}).eq(
                                    "id", row["id"]
                                ).execute()
                                st.success("Đã cập nhật số dư!")
                                st.rerun()
                        with col_b2:
                            if st.form_submit_button("🗑️ Xóa", use_container_width=True):
                                supabase.table("accounts").delete().eq("id", row["id"]).execute()
                                st.success("Đã xóa!")
                                st.rerun()

# ---------------------------------------------------------
# TAB 3: NHẬP GIAO DỊCH
# ---------------------------------------------------------
with tabs[2]:
    st.subheader("📝 Ghi Chép Thu / Chi Mới")
    if not categories_df.empty:
        trans_type = st.radio("Loại phát sinh", ["Chi tiêu 🔴", "Thu nhập 🟢"], horizontal=True)
        type_clean = "Chi tiêu" if "Chi tiêu" in trans_type else "Thu nhập"
        filtered_cats = categories_df[categories_df["type"] == type_clean]

        with st.form("misa_add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                t_date = st.date_input("Ngày thực hiện", datetime.date.today())
                category_selected = st.selectbox("Hạng mục thu/chi", filtered_cats["name"].tolist())

            with col2:
                amount = st.number_input("Số tiền phát sinh (VNĐ)", min_value=0, step=50000, format="%d")
                note = st.text_input("Ghi chú chi tiết", placeholder="Ví dụ: Đổ xăng xe i10, Mua sách...")

            submitted = st.form_submit_button("💾 Ghi Sổ Ngay", use_container_width=True)

            if submitted:
                if amount <= 0:
                    st.error("Vui lòng nhập số tiền hợp lệ!")
                else:
                    cat_id = int(filtered_cats[filtered_cats["name"] == category_selected]["id"].values[0])
                    data = {
                        "transaction_date": str(t_date),
                        "amount": amount,
                        "category_id": cat_id,
                        "note": note,
                    }
                    supabase.table("transactions").insert(data).execute()
                    st.success(f"Đã lưu khoản {category_selected}: {format_vnd(amount)}")
                    st.rerun()

# ---------------------------------------------------------
# TAB 4: DỰ KIẾN THU CHI THEO THÁNG / NĂM
# ---------------------------------------------------------
with tabs[3]:
    st.subheader("🎯 Bảng Thiết Lập Dự Kiến Thu & Chi Theo Tháng")

    selected_year = st.number_input("Chọn năm kế hoạch", min_value=2020, max_value=2035, value=datetime.date.today().year)

    if not categories_df.empty:
        budgets_existing = get_budgets(selected_year)
        existing_m_dict = {}
        if not budgets_existing.empty and "monthly_amount" in budgets_existing.columns:
            existing_m_dict = dict(zip(budgets_existing["category_id"], budgets_existing["monthly_amount"]))

        with st.expander("⚙️ Điều Chỉnh Cụ Thể Mức Dự Kiến Cho Từng Mục (Tính Theo THÁNG)", expanded=True):
            with st.form("monthly_budget_form"):
                st.markdown("#### 🟢 1. Dự Kiến THU NHẬP Hàng Tháng")
                inc_cats = categories_df[categories_df["type"] == "Thu nhập"]
                new_m_budgets = {}

                if not inc_cats.empty:
                    col_i1, col_i2 = st.columns(2)
                    for idx, (_, row) in enumerate(inc_cats.iterrows()):
                        cat_id, cat_name = row["id"], row["name"]
                        def_val = float(existing_m_dict.get(cat_id, 0))
                        target_col = col_i1 if idx % 2 == 0 else col_i2
                        val = target_col.number_input(
                            f"Dự kiến THU / THÁNG: '{cat_name}'", min_value=0.0, value=def_val, step=500000.0, format="%.0f"
                        )
                        new_m_budgets[cat_id] = val

                st.markdown("---")
                st.markdown("#### 🔴 2. Dự Kiến CHI TIÊU Hàng Tháng")
                exp_cats = categories_df[categories_df["type"] == "Chi tiêu"]

                if not exp_cats.empty:
                    col_e1, col_e2 = st.columns(2)
                    for idx, (_, row) in enumerate(exp_cats.iterrows()):
                        cat_id, cat_name = row["id"], row["name"]
                        def_val = float(existing_m_dict.get(cat_id, 0))
                        target_col = col_e1 if idx % 2 == 0 else col_e2
                        val = target_col.number_input(
                            f"Dự kiến CHI / THÁNG: '{cat_name}'", min_value=0.0, value=def_val, step=200000.0, format="%.0f"
                        )
                        new_m_budgets[cat_id] = val

                if st.form_submit_button("💾 Lưu Kế Hoạch Dự Kiến Theo Tháng", use_container_width=True):
                    for cat_id, m_val in new_m_budgets.items():
                        annual_val = m_val * 12
                        data = {
                            "year": int(selected_year),
                            "category_id": int(cat_id),
                            "monthly_amount": m_val,
                            "planned_amount": annual_val,
                        }
                        supabase.table("annual_budgets").upsert(data, on_conflict="year,category_id").execute()
                    st.success("Đã lưu mức dự kiến theo tháng thành công!")
                    st.rerun()

        st.markdown(f"### 📊 Báo Cáo Tiến Độ Thực Hiện Theo Dự Kiến (Năm {selected_year})")

        m_view = st.selectbox("Xem so sánh theo", ["Dự kiến Trung Bình 1 Tháng", "Dự kiến Cả Năm (12 Tháng)"])

        budgets_df = get_budgets(selected_year)
        trans_year_df = get_transactions(year=selected_year)

        if not budgets_df.empty:
            actual_df = (
                trans_year_df.groupby("category_id")["amount"].sum().reset_index()
                if not trans_year_df.empty
                else pd.DataFrame(columns=["category_id", "amount"])
            )
            merged = pd.merge(budgets_df, actual_df, on="category_id", how="left").fillna({"amount": 0})

            c_inc, c_exp = st.columns(2)

            is_monthly = m_view == "Dự kiến Trung Bình 1 Tháng"

            with c_inc:
                st.markdown("##### 🟢 Kế Hoạch THU NHẬP")
                inc_merged = merged[merged["type"] == "Thu nhập"]
                for _, row in inc_merged.iterrows():
                    target_val = float(row["monthly_amount"]) if is_monthly else float(row["planned_amount"])
                    actual_val = (
                        float(row["amount"]) / 12 if is_monthly and not trans_year_df.empty else float(row["amount"])
                    )

                    if target_val > 0:
                        pct = min(1.0, actual_val / target_val)
                        st.write(
                            f"**{row['category_name']}**: {format_vnd(actual_val)} / {format_vnd(target_val)} ({pct*100:.1f}%)"
                        )
                        st.progress(pct)

            with c_exp:
                st.markdown("##### 🔴 Kế Hoạch CHI TIÊU")
                exp_merged = merged[merged["type"] == "Chi tiêu"]
                for _, row in exp_merged.iterrows():
                    target_val = float(row["monthly_amount"]) if is_monthly else float(row["planned_amount"])
                    actual_val = (
                        float(row["amount"]) / 12 if is_monthly and not trans_year_df.empty else float(row["amount"])
                    )

                    if target_val > 0:
                        pct = min(1.0, actual_val / target_val)
                        st.write(
                            f"**{row['category_name']}**: {format_vnd(actual_val)} / {format_vnd(target_val)} ({pct*100:.1f}%)"
                        )
                        st.progress(pct)
                        if actual_val > target_val:
                            st.caption(f"🚨 Đã vượt dự kiến: **{format_vnd(actual_val - target_val)}**")

# ---------------------------------------------------------
# TAB 5: ĐIỀU CHỈNH HOẶC XÓA GIAO DỊCH
# ---------------------------------------------------------
with tabs[4]:
    st.subheader("🛠️ Chỉnh Sửa Ghi Chú & Điều Chỉnh Giao Dịch")
    all_trans = get_transactions()

    if not all_trans.empty:
        all_trans = all_trans.sort_values(by="transaction_date", ascending=False)
        trans_options = {
            row[
                "id"
            ]: f"ID {row['id']} | {row['transaction_date'].strftime('%Y-%m-%d')} | {row['category_name']} | {format_vnd(row['amount'])} | Ghi chú: {row['note']}"
            for _, row in all_trans.iterrows()
        }

        selected_trans_id = st.selectbox(
            "Chọn giao dịch cần điều chỉnh / xóa", list(trans_options.keys()), format_func=lambda x: trans_options[x]
        )
        selected_row = all_trans[all_trans["id"] == selected_trans_id].iloc[0]

        with st.form("edit_transaction_form"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_date = st.date_input("Ngày giao dịch", selected_row["transaction_date"])
                e_amount = st.number_input(
                    "Số tiền (VNĐ)", min_value=0, value=int(selected_row["amount"]), step=10000, format="%d"
                )

            with col_e2:
                cat_list = categories_df["name"].tolist()
                curr_cat_idx = (
                    cat_list.index(selected_row["category_name"]) if selected_row["category_name"] in cat_list else 0
                )
                e_cat_name = st.selectbox("Danh mục", cat_list, index=curr_cat_idx)
                e_note = st.text_input("Ghi chú", value=str(selected_row["note"] if selected_row["note"] else ""))

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.form_submit_button("💾 Cập Nhật Giao Dịch", use_container_width=True):
                    new_cat_id = int(categories_df[categories_df["name"] == e_cat_name]["id"].values[0])
                    supabase.table("transactions").update(
                        {
                            "transaction_date": str(e_date),
                            "amount": e_amount,
                            "category_id": new_cat_id,
                            "note": e_note,
                        }
                    ).eq("id", selected_trans_id).execute()
                    st.success("Đã cập nhật giao dịch thành công!")
                    st.rerun()

            with col_btn2:
                if st.form_submit_button("🗑️ Xóa Giao Dịch Này", use_container_width=True):
                    supabase.table("transactions").delete().eq("id", selected_trans_id).execute()
                    st.success("Đã xóa giao dịch thành công!")
                    st.rerun()

# ---------------------------------------------------------
# TAB 6: QUẢN LÝ / SỬA / XÓA DANH MỤC
# ---------------------------------------------------------
with tabs[5]:
    st.subheader("⚙️ Quản Lý & Chỉnh Sửa Danh Mục")
    col_c1, col_c2 = st.columns([1, 1])

    with col_c1:
        st.markdown("##### ➕ Thêm danh mục mới")
        with st.form("cat_misa_add", clear_on_submit=True):
            cat_name = st.text_input("Tên danh mục mới", placeholder="Ví dụ: Dạy thêm, Tiền tã bỉm, Sửa xe i10...")
            cat_type = st.selectbox("Loại danh mục", ["Chi tiêu", "Thu nhập"])

            if st.form_submit_button("➕ Thêm Danh Mục", use_container_width=True):
                if cat_name.strip():
                    supabase.table("categories").insert({"name": cat_name.strip(), "type": cat_type}).execute()
                    st.success(f"Đã thêm danh mục: **{cat_name}**")
                    st.rerun()

    with col_c2:
        st.markdown("##### ✏️ Đổi Tên / Phân Loại Hoặc Xóa Danh Mục")
        if not categories_df.empty:
            cat_edit_options = {row["id"]: f"{row['name']} ({row['type']})" for _, row in categories_df.iterrows()}
            selected_cat_id = st.selectbox("Chọn danh mục cần sửa", list(cat_edit_options.keys()), format_func=lambda x: cat_edit_options[x])

            cat_to_edit = categories_df[categories_df["id"] == selected_cat_id].iloc[0]

            with st.form(f"edit_cat_form_{selected_cat_id}"):
                edited_name = st.text_input("Tên danh mục", value=str(cat_to_edit["name"]))
                type_options = ["Chi tiêu", "Thu nhập"]
                curr_type_idx = type_options.index(cat_to_edit["type"]) if cat_to_edit["type"] in type_options else 0
                edited_type = st.selectbox("Phân loại", type_options, index=curr_type_idx)

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.form_submit_button("💾 Cập Nhật Danh Mục", use_container_width=True):
                        if edited_name.strip():
                            supabase.table("categories").update(
                                {"name": edited_name.strip(), "type": edited_type}
                            ).eq("id", selected_cat_id).execute()
                            st.success("Đã cập nhật danh mục!")
                            st.rerun()
                with btn_col2:
                    if st.form_submit_button("🗑️ Xóa Danh Mục", use_container_width=True):
                        supabase.table("categories").delete().eq("id", selected_cat_id).execute()
                        st.success("Đã xóa danh mục!")
                        st.rerun()