import streamlit as st
import pandas as pd
from google import genai
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import os

st.set_page_config(page_title="Universal Safety & Inspection Atlas", layout="wide")

# Yon panel sozlamalari
api_key = st.sidebar.text_input("Gemini API kalitini kiriting:", type="password")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Universal Platform:** Weigh Station xaritalari, ma'lumotlar tahlili va interaktiv hisobotlar.")

# Session State: Ma'lumotlarni saqlab qolish
if "ws_data" not in st.session_state:
    st.session_state["ws_data"] = None

if "analysis_data" not in st.session_state:
    st.session_state["analysis_data"] = None

# 3 ta asosiy bo'lim (Tabs)
tab1, tab2, tab3 = st.tabs([
    "🗺️ Inspection Atlas & Interactive Maps", 
    "⚖️ USA Weigh Stations Map", 
    "📊 Data Analyzer & AI Rule Finder"
])

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

# ----------------- 2-BO'LIM: USA WEIGH STATIONS MAP -----------------
with tab2:
    st.subheader("⚖️ USA Weigh Stations — Interaktiv Xarita")
    st.write("AQSH bo'yicha Weigh Station ma'lumotlari (CSV, Excel yoki Parquet) faylini yuklang. Ma'lumotlar brauzeringizda saqlanib qoladi.")

    supported_types = ["csv", "tsv", "xlsx", "xls", "parquet", "json"]
    ws_file = st.file_uploader("Weigh Stations bazasini yuklang:", type=supported_types, key="ws_uploader")

    if ws_file:
        file_name = ws_file.name.lower()
        try:
            with st.spinner("Stansiyalar o'qilmoqda..."):
                if file_name.endswith('.csv'):
                    st.session_state["ws_data"] = pd.read_csv(ws_file, low_memory=False)
                elif file_name.endswith('.tsv'):
                    st.session_state["ws_data"] = pd.read_csv(ws_file, sep='\t', low_memory=False)
                elif file_name.endswith('.parquet'):
                    st.session_state["ws_data"] = pd.read_parquet(ws_file)
                elif file_name.endswith('.json'):
                    st.session_state["ws_data"] = pd.read_json(ws_file)
                elif any(file_name.endswith(ext) for ext in ['.xlsx', '.xls']):
                    xls = pd.ExcelFile(ws_file)
                    selected_sheet = st.selectbox("Varaqni tanlang:", xls.sheet_names, key="ws_sheet")
                    st.session_state["ws_data"] = pd.read_excel(ws_file, sheet_name=selected_sheet)
            st.success(f"Ma'lumotlar muvaffaqiyatli saqlandi! ({len(st.session_state['ws_data']):,} ta yozuv)")
        except Exception as e:
            st.error(f"Faylni yuklashda xatolik: {e}")

    # Agar ma'lumot yuklangan bo'lsa xaritani ko'rsatish
    ws_df = st.session_state["ws_data"]
    if ws_df is not None and not ws_df.empty:
        cols = ws_df.columns.tolist()

        # Koordinata ustunlarini avtomatik topish
        lat_candidates = [c for c in cols if any(k in str(c).lower() for k in ['lat', 'latitude', 'y_coord', 'latitude_deg'])]
        lon_candidates = [c for c in cols if any(k in str(c).lower() for k in ['lon', 'lng', 'longitude', 'x_coord', 'longitude_deg'])]

        c1, c2, c3 = st.columns(3)
        with c1:
            lat_col = st.selectbox("Latitude (Kenglik) ustuni:", options=cols, index=cols.index(lat_candidates[0]) if lat_candidates else 0)
        with c2:
            lon_col = st.selectbox("Longitude (Uzunlik) ustuni:", options=cols, index=cols.index(lon_candidates[0]) if lon_candidates else (1 if len(cols) > 1 else 0))
        with c3:
            name_candidates = [c for c in cols if any(k in str(c).lower() for k in ['name', 'station', 'location', 'site', 'facility'])]
            name_col = st.selectbox("Stansiya nomi / Tavsif ustuni:", options=cols, index=cols.index(name_candidates[0]) if name_candidates else 0)

        # Shtat bo'yicha tezkor filtr
        state_candidates = [c for c in cols if any(k in str(c).lower() for k in ['state', 'st', 'jurisdiction'])]
        filtered_ws = ws_df.copy()
        if state_candidates:
            st_col = state_candidates[0]
            unique_states = ["Barchasi"] + sorted(ws_df[st_col].dropna().astype(str).unique().tolist())
            selected_st = st.selectbox("Shtat bo'yicha saralash:", unique_states)
            if selected_st != "Barchasi":
                filtered_ws = filtered_ws[filtered_ws[st_col].astype(str) == selected_st]

        # Sonli koordinatalarga aylantirish va bo'shlarini tozalash
        filtered_ws[lat_col] = pd.to_numeric(filtered_ws[lat_col], errors='coerce')
        filtered_ws[lon_col] = pd.to_numeric(filtered_ws[lon_col], errors='coerce')
        valid_map_data = filtered_ws.dropna(subset=[lat_col, lon_col])

        st.caption(f"Xaritada aks ettirilayotgan stansiyalar soni: **{len(valid_map_data):,}** ta")

        if not valid_map_data.empty:
            # USA markazida xarita yaratish
            m = folium.Map(location=[39.8283, -98.5795], zoom_start=4, tiles="OpenStreetMap")
            marker_cluster = MarkerCluster().add_to(m)

            # Tezlik uchun ko'pi bilan 3000 ta nuqtani klasterga berish
            plot_limit = min(len(valid_map_data), 3000)
            sample_points = valid_map_data.head(plot_limit)

            for _, row in sample_points.iterrows():
                lat = row[lat_col]
                lon = row[lon_col]
                station_label = str(row[name_col])
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(f"<b>{station_label}</b><br>Lat: {lat}<br>Lon: {lon}", max_width=250),
                    tooltip=station_label,
                    icon=folium.Icon(color="darkblue", icon="scale", prefix="fa")
                ).add_to(marker_cluster)

            st_folium(m, width=1300, height=650)
            
            with st.expander("📋 Stansiyalar ma'lumotlar jadvali"):
                st.dataframe(valid_map_data.head(200))
        else:
            st.warning("Tanlangan ustunlarda to'g'ri raqamli koordinatalar (Latitude / Longitude) topilmadi.")
    else:
        st.info("Iltimos, Weigh Station nuqtalari mavjud bo'lgan faylni yuklang.")

# ----------------- 3-BO'LIM: DATA ANALYZER & GEMINI -----------------
with tab3:
    st.subheader("📊 Data Analyzer & AI Rule Finder (Saralash va Qoliplar)")
    
    supported_types = [
        "csv", "tsv", "txt", "tab",
        "xlsx", "xls", "xlsm", "xlsb", "ods",
        "parquet", "feather", "ftr",
        "json", "jsonl", "ndjson",
        "gz", "zip"
    ]
    
    analysis_file = st.file_uploader(
        "Tahlil qilinadigan faylni yuklang (CSV, Excel, Parquet, JSON, TSV...):", 
        type=supported_types,
        key="analysis_uploader"
    )

    if analysis_file:
        file_name = analysis_file.name.lower()
        try:
            with st.spinner("Tahlil ma'lumotlari o'qilmoqda..."):
                if any(file_name.endswith(ext) for ext in ['.csv', '.txt', '.gz', '.zip']):
                    st.session_state["analysis_data"] = pd.read_csv(analysis_file, low_memory=False)
                elif any(file_name.endswith(ext) for ext in ['.tsv', '.tab']):
                    st.session_state["analysis_data"] = pd.read_csv(analysis_file, sep='\t', low_memory=False)
                elif file_name.endswith('.parquet'):
                    st.session_state["analysis_data"] = pd.read_parquet(analysis_file)
                elif any(file_name.endswith(ext) for ext in ['.feather', '.ftr']):
                    st.session_state["analysis_data"] = pd.read_feather(analysis_file)
                elif any(file_name.endswith(ext) for ext in ['.jsonl', '.ndjson']):
                    st.session_state["analysis_data"] = pd.read_json(analysis_file, lines=True)
                elif file_name.endswith('.json'):
                    st.session_state["analysis_data"] = pd.read_json(analysis_file)
                elif any(file_name.endswith(ext) for ext in ['.xlsx', '.xls', '.xlsm', '.xlsb', '.ods']):
                    xls = pd.ExcelFile(analysis_file)
                    selected_sheet = st.selectbox("Kerakli varaqni tanlang:", xls.sheet_names, key="analysis_sheet")
                    st.session_state["analysis_data"] = pd.read_excel(analysis_file, sheet_name=selected_sheet)
        except Exception as e:
            st.error(f"Faylni o'qishda xatolik: {e}")

    df = st.session_state["analysis_data"]

    if df is not None and not df.empty:
        total_rows = len(df)
        st.success(f"Ma'lumotlar saqlandi! Qatorlar: {total_rows:,} ta | Ustunlar: {len(df.columns)} ta")

        st.write("### 1. Ma'lumotlarni saralash va filtrlash")
        all_columns = df.columns.tolist()

        filter_col = st.selectbox("Saralash uchun ustunni tanlang (Masalan: State, Level, Violation Code):", ["Hech qaysi"] + all_columns)
        filtered_df = df
        if filter_col != "Hech qaysi":
            unique_vals = df[filter_col].dropna().unique().tolist()
            selected_val = st.multiselect(f"{filter_col} bo'yicha qiymatlarni tanlang:", options=unique_vals, default=unique_vals[:5] if len(unique_vals) > 5 else unique_vals)
            filtered_df = df[df[filter_col].isin(selected_val)]

        st.dataframe(filtered_df.head(10))

        st.write("### 2. Tahlil doirasi (Range va Cheklov)")
        col_r1, col_r2 = st.columns([1, 2])
        with col_r1:
            analyze_all = st.checkbox("Barcha saralangan qatorlarni tahlil qilish", value=(len(filtered_df) <= 100000))
        with col_r2:
            sample_limit = st.slider(
                "Tahlil qilinadigan qatorlar chegarasi (Limit):", 
                min_value=1000, 
                max_value=max(len(filtered_df), 1000), 
                value=min(len(filtered_df), 50000),
                step=1000,
                disabled=analyze_all
            )

        analysis_df = filtered_df if analyze_all else filtered_df.head(sample_limit)
        st.caption(f"Tanlangan tahlil hajmi: **{len(analysis_df):,}** ta qator")

        st.write("### 3. Bog'liqliklar uchun ustunlarni belgilash")
        selected_columns = st.multiselect(
            "Qoliplarni aniqlash ustunlari (Masalan: County, Location, Facility, Address):",
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
    else:
        st.info("Saralash va tahlil qilish uchun fayl yuklang.")
