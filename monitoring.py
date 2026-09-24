import streamlit as st
import pandas as pd
from google import genai
import streamlit.components.v1 as components
import os

# Sahifa kengligi va sarlavhasi
st.set_page_config(page_title="Universal Safety & Inspection Atlas", layout="wide")

# Yon panel sozlamalari
api_key = st.sidebar.text_input("Gemini API kalitini kiriting:", type="password")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Universal Platform:** Ma'lumotlarni tahlil qilish va xarita atlasidan bitta joyda foydalaning.")

# 2 ta asosiy bo'lim (Tabs)
tab1, tab2 = st.tabs(["🗺️ Inspection Atlas & Interactive Maps", "📊 Data Analyzer & AI Rule Finder"])

# ----------------- 1-BO'LIM: INTERACTIVE HTML ATLAS -----------------
with tab1:
    st.subheader("Inspection Atlas — Weigh Station, Corridors & Driver Reports")
    
    html_file_path = "Inspection_Atlas_Driver_Reports final 2.html"
    
    if os.path.exists(html_file_path):
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=1050, scrolling=True)
    else:
        st.warning(f"⚠️ `{html_file_path}` fayli topilmadi. Faylni to'g'ri nom bilan yuklaganingizga ishonch hosil qiling.")

# ----------------- 2-BO'LIM: DATA ANALYZER & GEMINI -----------------
with tab2:
    st.subheader("Vehicle Inspection & Address Pattern Generator")
    uploaded_file = st.file_uploader("Katta hajmdagi faylni yuklang (CSV yoki Excel)", type=["csv", "xlsx", "xls"])

    if uploaded_file:
        st.info("Fayl tahlil qilinmoqda...")
        df = None
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            selected_sheet = st.selectbox("Kerakli varaqni (Sheet) tanlang:", sheet_names)
            with st.spinner("Jadval yuklanmoqda..."):
                df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

        if df is not None and not df.empty:
            st.success(f"Fayl muvaffaqiyatli yuklandi! Jami qatorlar soni: {len(df):,}")
            st.write("### 1. Ma'lumotlardan namuna")
            st.dataframe(df.head(10))

            all_columns = df.columns.tolist()
            selected_columns = st.multiselect(
                "Tahlil qilinadigan ustunlarni tanlang:",
                options=all_columns,
                default=[col for col in all_columns if any(k in str(col).lower() for k in ['county', 'location', 'facil', 'address', 'site', 'hwy', 'road'])][:4]
            )

            if len(selected_columns) >= 2:
                patterns = df.groupby(selected_columns, dropna=False).size().reset_index(name='Takrorlanish_soni')
                patterns = patterns.sort_values(by='Takrorlanish_soni', ascending=False)
                st.write(f"### 2. Ajratib olingan noyob qoliplar ({len(patterns):,} ta pattern)")
                st.dataframe(patterns.head(50))

                if st.button("🤖 Gemini orqali qoidalarni aniqlash"):
                    if not api_key:
                        st.error("Iltimos, chap tarafdagi maydonga Gemini API kalitingizni kiriting!")
                    else:
                        client = genai.Client(api_key=api_key)
                        sample_data = patterns.head(40).to_string(index=False)
                        prompt = f"""
                        Quyidagi xavfsizlik (Safety / Vehicle Inspection) ma'lumotlaridagi qonuniyatlarni tahlil qil.
                        Ustunlar: {', '.join(selected_columns)}
                        
                        Qat'iy mantiqiy qoidalar ro'yxatini tuz:
                        IF {selected_columns[0]}=... AND {selected_columns[1]}=... THEN ...
                        
                        Qoliplar namunasi:
                        {sample_data}
                        """
                        with st.spinner("Gemini tahlil qilmoqda..."):
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=prompt,
                            )
                            st.write("### 3. Aniqlangan mantiqiy qoidalar:")
                            st.markdown(response.text)
            else:
                st.warning("Iltimos, kamida 2 ta ustunni tanlang.")
        else:
            st.error("Varaq bo'sh yoki ma'lumotlarni o'qib bo'lmadi.")
