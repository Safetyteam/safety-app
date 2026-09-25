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
# ----------------- 2-BO'LIM: USA WEIGH STATIONS MAP -----------------
with tab2:
    st.subheader("⚖️ USA Weigh Stations — Interaktiv Xarita")
    st.write("Weigh Station yoki ko'riklar faylini yuklang. Agar koordinata bo'lmasa, dastur shahar/stansiya nomidan koordinatalarni avtomatik aniqlaydi.")

    supported_types = ["csv", "tsv", "xlsx", "xls", "parquet", "json"]
    ws_file = st.file_uploader("Faylni yuklang (CSV, Excel):", type=supported_types, key="ws_uploader")

    if ws_file:
        file_name = ws_file.name.lower()
        try:
            with st.spinner("Ma'lumotlar o'qilmoqda..."):
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
            st.success(f"Ma'lumotlar muvaffaqiyatli yuklandi! ({len(st.session_state['ws_data']):,} ta yozuv)")
        except Exception as e:
            st.error(f"Faylni yuklashda xatolik: {e}")

    ws_df = st.session_state.get("ws_data")
    if ws_df is not None and not ws_df.empty:
        cols = ws_df.columns.tolist()

        # 1. Koordinata ustunlarini qidirish
        lat_candidates = [c for c in cols if any(k in str(c).lower() for k in ['lat', 'latitude', 'y_coord'])]
        lon_candidates = [c for c in cols if any(k in str(c).lower() for k in ['lon', 'lng', 'longitude', 'x_coord'])]
        
        # 2. Joylashuv nomi ustunini topish (LOCATION_DESC, LOCATION, CITY, STATION)
        desc_candidates = [c for c in cols if any(k in str(c).lower() for k in ['desc', 'location', 'station', 'city', 'site', 'name'])]
        
        c1, c2 = st.columns(2)
        with c1:
            name_col = st.selectbox("Stansiya / Joylashuv ustuni:", options=cols, index=cols.index(desc_candidates[0]) if desc_candidates else 0)
        with c2:
            count_candidates = [c for c in cols if any(k in str(c).lower() for k in ['soni', 'count', 'total', 'takrorlanish'])]
            count_col = st.selectbox("Ko'riklar soni ustuni (ixtiyoriy):", options=["Yo'q"] + cols, index=cols.index(count_candidates[0])+1 if count_candidates else 0)

        # AQSH shtatlari va mashhur Weigh Station/shaharlari rasmiy koordinatalar lug'ati
        KNOWN_LOCATIONS = {
            "MAYVIEW MO": (39.0142, -93.8341),
            "JOPLIN MO": (37.0842, -94.5133),
            "CHARLESTON MO": (36.9206, -89.3331),
            "STEELE MO": (36.0859, -89.8315),
            "WILLOW SPRINGS MO": (36.9926, -91.9668),
            "ST CLAIR MO": (38.3456, -90.9818),
            "EAGLEVILLE MO": (40.5486, -93.9855),
            "FORISTELL MO": (38.8239, -90.9579),
            "ST GENEVIEVE MO": (37.9781, -90.0468),
            "STE GENEVIEVE MO": (37.9781, -90.0468),
            "WENTZVILLE MO": (38.8106, -90.8529),
            "NEOSHO MO": (36.8687, -94.3683),
            "GRANBY MO": (36.9184, -94.2547),
            "BOONVILLE MO": (38.9736, -92.7432),
            "HARRISONVILLE MO": (38.6533, -94.3488),
            "PLATTSBURG MO": (39.5636, -94.4608),
            "BLOOMFIELD MO": (36.8856, -89.9284),
            "CAMERON MO": (39.7408, -94.2377),
        }

        # Agar asl jadvalda koordinata bo'lmasa, uni nom bo'yicha to'ldirish
        df_mapped = ws_df.copy()
        
        has_real_coords = bool(lat_candidates and lon_candidates)
        if has_real_coords:
            lat_col = lat_candidates[0]
            lon_col = lon_candidates[0]
            df_mapped['lat_val'] = pd.to_numeric(df_mapped[lat_col], errors='coerce')
            df_mapped['lon_val'] = pd.to_numeric(df_mapped[lon_col], errors='coerce')
        else:
            df_mapped['lat_val'] = None
            df_mapped['lon_val'] = None

        # Rasmiy geolokatsiya orqali koordinatalarni ulash
        for idx, row in df_mapped.iterrows():
            if pd.isna(row['lat_val']) or pd.isna(row['lon_val']):
                loc_text = str(row[name_col]).strip().upper()
                # To'liq mos kelishini tekshirish
                if loc_text in KNOWN_LOCATIONS:
                    df_mapped.at[idx, 'lat_val'] = KNOWN_LOCATIONS[loc_text][0]
                    df_mapped.at[idx, 'lon_val'] = KNOWN_LOCATIONS[loc_text][1]
                else:
                    # Qisman moslik (masalan "MAYVIEW" so'zi qatnashgan bo'lsa)
                    for k, coords in KNOWN_LOCATIONS.items():
                        if k.split()[0] in loc_text:
                            df_mapped.at[idx, 'lat_val'] = coords[0]
                            df_mapped.at[idx, 'lon_val'] = coords[1]
                            break

        valid_points = df_mapped.dropna(subset=['lat_val', 'lon_val'])
        st.info(f"📍 Xaritada aks ettirilayotgan stansiyalar soni: **{len(valid_points)}** / {len(ws_df)} ta")

        if not valid_points.empty:
            # Xarita markazini o'rtacha nuqtaga moslash
            avg_lat = valid_points['lat_val'].mean()
            avg_lon = valid_points['lon_val'].mean()
            
            m = folium.Map(location=[avg_lat, avg_lon], zoom_start=6, tiles="OpenStreetMap")
            marker_cluster = MarkerCluster().add_to(m)

            for _, r in valid_points.iterrows():
                lat = r['lat_val']
                lon = r['lon_val']
                title = f"{r[name_col]}"
                if 'LOCATION' in r:
                    title = f"[{r['LOCATION']}] - {title}"
                count_info = f"<br>Ko'riklar soni: <b>{r[count_col]}</b>" if count_col != "Yo'q" and pd.notna(r[count_col]) else ""

                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(f"<b>Weigh Station:</b> {title}{count_info}<br>Lat: {lat:.4f}, Lon: {lon:.4f}", max_width=300),
                    tooltip=title,
                    icon=folium.Icon(color="red", icon="truck", prefix="fa")
                ).add_to(marker_cluster)

            st_folium(m, width=1300, height=620)
            
            with st.expander("📋 Joylashuvlar va Koordinatalar jadvali"):
                st.dataframe(valid_points[[c for c in cols if c in valid_points.columns] + ['lat_val', 'lon_val']])
        else:
            st.warning("⚠️ Fayldagi joylashuv nomlari (`LOCATION_DESC`) bo'yicha koordinatalar topilmadi.")

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
