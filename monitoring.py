import streamlit as st
import pandas as pd
from google import genai
import streamlit.components.v1 as components
import os

st.set_page_config(page_title="Universal Safety & Inspection Atlas", layout="wide")

# Yon panel
api_key = st.sidebar.text_input("Gemini API kalitini kiriting:", type="password")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Universal Platform (2GB Max):** CSV, Excel, Parquet, Feather, JSON, ODS, TSV, TXT, GZ fayllarini tahlil qilish.")

# Asosiy tablar
tab1, tab2 = st.tabs(["🗺️ Inspection Atlas & Interactive Maps", "📊 Data Analyzer & AI Rule Finder"])

# ----------------- 1-BO'LIM: ATLAS -----------------
with tab1:
    st.subheader("Inspection Atlas — Weigh Station, Corridors & Driver Reports")
    html_file_path = "Inspection_Atlas_Driver_Reports final 2.html"
    
    if os.path.exists(html_file_path):
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_data = f.read()

        st.download_button(
            label="📥 Atlasni to'liq ekranda / alohida ochish (HTML yuklab olish)",
            data=html_data,
            file_name="Inspection_Atlas_Full.html",
            mime="text/html"
        )
        st.info("💡 Xarita va ma'lumotlar hajmi katta bo'lgani uchun pastdagi oyna yengillashtirilgan rejimda ishlaydi.")
        components.html(html_data, height=900, scrolling=True)
    else:
        st.warning(f"⚠️ `{html_file_path}` fayli topilmadi.")

# ----------------- 2-BO'LIM: KATTA HAJMDAGI FAYLLAR TAHLILI -----------------
with tab2:
    st.subheader("Vehicle Inspection & Address Pattern Generator (Max 2GB)")
    
    # Qo'llab-quvvatlanadigan barcha formatlar
    supported_types = [
        "csv", "tsv", "txt", "tab",
        "xlsx", "xls", "xlsm", "xlsb", "ods",
        "parquet", "feather", "ftr",
        "json", "jsonl", "ndjson",
        "gz", "zip"
    ]
    
    uploaded_file = st.file_uploader(
        "Fayl yuklang (CSV, Excel, Parquet, Feather, JSON, ODS, TSV, GZ, ZIP)", 
        type=supported_types
    )

    if uploaded_file:
        file_name = uploaded_file.name.lower()
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.info(f"📁 Yuklangan fayl: `{uploaded_file.name}` ({file_size_mb:.2f} MB)")
        df = None

        try:
            with st.spinner("Katta hajmdagi ma'lumotlar o'qilmoqda..."):
                # 1. Delimiterli matnlar (CSV, TSV, TXT, GZ, ZIP)
                if any(file_name.endswith(ext) for ext in ['.csv', '.txt', '.gz', '.zip']):
                    df = pd.read_csv(uploaded_file, low_memory=False)
                elif any(file_name.endswith(ext) for ext in ['.tsv', '.tab']):
                    df = pd.read_csv(uploaded_file, sep='\t', low_memory=False)
                
                # 2. Apache Arrow / Parquet / Feather (Ultra-fast big data)
                elif file_name.endswith('.parquet'):
                    df = pd.read_parquet(uploaded_file)
                elif any(file_name.endswith(ext) for ext in ['.feather', '.ftr']):
                    df = pd.read_feather(uploaded_file)
                
                # 3. JSON formatlar
                elif any(file_name.endswith(ext) for ext in ['.jsonl', '.ndjson']):
                    df = pd.read_json(uploaded_file, lines=True)
                elif file_name.endswith('.json'):
                    df = pd.read_json(uploaded_file)
                
                # 4. Excel va Spreadsheet formatlar
                elif any(file_name.endswith(ext) for ext in ['.xlsx', '.xls', '.xlsm', '.xlsb', '.ods']):
                    xls = pd.ExcelFile(uploaded_file)
                    selected_sheet = st.selectbox("Kerakli varaqni (Sheet) tanlang:", xls.sheet_names)
                    df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
                    
        except Exception as e:
            st.error(f"Faylni o'qishda xatolik yuz berdi: {e}")

        if df is not None and not df.empty:
            total_rows = len(df)
            st.success(f"Fayl muvaffaqiyatli yuklandi! Jami qatorlar: {total_rows:,} ta, Ustunlar: {len(df.columns)} ta")
            
            st.write("### 1. Ma'lumotlardan dastlabki namuna")
            st.dataframe(df.head(10))

            all_columns = df.columns.tolist()
            
            # Dinamik Range tanlash (Katta massivlar uchun)
            st.write("### 2. Tahlil doirasi (Range va Qatorlar filtri)")
            col_r1, col_r2 = st.columns([1, 2])
            with col_r1:
                analyze_all = st.checkbox("Barcha qatorlarni to'liq tahlil qilish", value=(total_rows <= 100000))
            with col_r2:
                sample_limit = st.slider(
                    "Tahlil qilinadigan qatorlar chegarasi (Limit):", 
                    min_value=1000, 
                    max_value=min(total_rows, 2000000), 
                    value=min(total_rows, 100000),
                    step=5000,
                    disabled=analyze_all
                )

            analysis_df = df if analyze_all else df.head(sample_limit)
            st.caption(f"Hozirda tanlangan tahlil hajmi: **{len(analysis_df):,}** ta qator")

            # Ustunlarni tanlash
            st.write("### 3. Tahlil qilinadigan ustunlarni belgilang")
            selected_columns = st.multiselect(
                "Ustunlarni tanlang (masalan: County, Location, Facility, Address):",
                options=all_columns,
                default=[col for col in all_columns if any(k in str(col).lower() for k in ['county', 'location', 'facil', 'address', 'site', 'hwy', 'road', 'violation'])][:4]
            )

            if len(selected_columns) >= 2:
                patterns = analysis_df.groupby(selected_columns, dropna=False).size().reset_index(name='Takrorlanish_soni')
                patterns = patterns.sort_values(by='Takrorlanish_soni', ascending=False)
                
                st.write(f"### 4. Ajratib olingan noyob qoliplar ({len(patterns):,} ta pattern)")
                st.dataframe(patterns.head(100))

                if st.button("🤖 Gemini orqali qoidalarni aniqlash"):
                    if not api_key:
                        st.error("Iltimos, chap tarafdagi maydonga Gemini API kalitingizni kiriting!")
                    else:
                        client = genai.Client(api_key=api_key)
                        sample_data = patterns.head(50).to_string(index=False)
                        prompt = f"""
                        Quyidagi xavfsizlik (Safety / Vehicle Inspection) ma'lumotlaridagi qonuniyatlarni chuqur tahlil qil.
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
                            st.write("### 5. Aniqlangan mantiqiy qoidalar:")
                            st.markdown(response.text)
            else:
                st.warning("Iltimos, kamida 2 ta ustunni tanlang.")
        elif df is not None and df.empty:
            st.error("Fayl bo'sh yoki ma'lumotlarni o'qib bo'lmadi.")
            st.error("Varaq bo'sh yoki ma'lumotlarni o'qib bo'lmadi.")
