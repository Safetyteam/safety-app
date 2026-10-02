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
    st.write("Weigh Station yoki ko'riklar faylini yuklang. Dastur kod va shahar nomi orqali rasmiy trassa koordinatalarini avtomatik belgilaydi.")

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

        # Ustunlarni aniqlash
        lat_candidates = [c for c in cols if any(k in str(c).lower() for k in ['lat', 'latitude', 'y_coord'])]
        lon_candidates = [c for c in cols if any(k in str(c).lower() for k in ['lon', 'lng', 'longitude', 'x_coord'])]
        desc_candidates = [c for c in cols if any(k in str(c).lower() for k in ['desc', 'location', 'station', 'city', 'site', 'name'])]
        
        c1, c2 = st.columns(2)
        with c1:
            name_col = st.selectbox("Stansiya / Joylashuv ustuni:", options=cols, index=cols.index(desc_candidates[0]) if desc_candidates else 0)
        with c2:
            count_candidates = [c for c in cols if any(k in str(c).lower() for k in ['soni', 'count', 'total', 'takrorlanish'])]
            count_col = st.selectbox("Ko'riklar soni ustuni (ixtiyoriy):", options=["Yo'q"] + cols, index=cols.index(count_candidates[0])+1 if count_candidates else 0)

        # Aniq trassa (Interstate) Weigh Station koordinatalari
        EXACT_STATIONS = {
            # EAGLEVILLE (H2, H2S - I-35 SB Welcome Center / Weigh Scale)
            ("H2", "EAGLEVILLE MO"): (40.5489, -93.9748),
            ("H2S", "EAGLEVILLE MO"): (40.5489, -93.9748),
            ("H2", ""): (40.5489, -93.9748),
            ("H2S", ""): (40.5489, -93.9748),

            # MAYVIEW (A3, A3E, A3W, A3EAST - I-70 EB / WB Scale MM 45)
            ("A3E", "MAYVIEW MO"): (39.0145, -93.8182),
            ("A3EAST", "MAYVIEW MO"): (39.0145, -93.8182),
            ("A3W", "MAYVIEW MO"): (39.0152, -93.8345),
            ("A3", "MAYVIEW MO"): (39.0148, -93.8260),

            # FORISTELL (C4W - I-70 WB Scale MM 206)
            ("C4W", "FORISTELL MO"): (38.8285, -90.9332),

            # ST CLAIR (C2E, C2W - I-44 EB / WB MM 245)
            ("C2E", "ST CLAIR MO"): (38.3582, -90.9635),
            ("C2W", "ST CLAIR MO"): (38.3591, -90.9712),

            # JOPLIN (D4E - I-44 EB Scale MM 4)
            ("D4E", "JOPLIN MO"): (37.0425, -94.5772),

            # CHARLESTON (E1S - I-57 SB MM 13)
            ("E1S", "CHARLESTON MO"): (36.8835, -89.3620),

            # STEELE (E2N - I-55 NB MM 4)
            ("E2N", "STEELE MO"): (36.0848, -89.8322),

            # WILLOW SPRINGS (G1W - US 60 / US 63 Junction)
            ("G1W", "WILLOW SPRINGS MO"): (36.9855, -91.9565),

            # STE / ST GENEVIEVE (C5S - I-55 SB MM 141)
            ("C5S", "ST GENEVIEVE MO"): (37.9542, -90.0988),
            ("C5S", "STE GENEVIEVE MO"): (37.9542, -90.0988),

            # WENTZVILLE (W147 - US 61 / I-70 Scale)
            ("W147", "WENTZVILLE MO"): (38.8256, -90.8752),

            # NEOSHO & GRANBY (US 71 / I-49 & US 60)
            ("49 20", "NEOSHO MO"): (36.8322, -94.3755),
            ("MO 59/", "GRANBY MO"): (36.9184, -94.2547),
            ("HARRISONVILLE", "HARRISONVILLE MO"): (38.6322, -94.3412),
            ("CAMERON", "CAMERON MO"): (39.7355, -94.2422),
            ("BOONVILLE", "BOONVILLE MO"): (38.9482, -92.7485),
            ("BLOOMFIELD", "BLOOMFIELD MO"): (36.8856, -89.9284),
        }

        # Shahar nomiga asoslangan zaxira nuqtalar
        CITY_FALLBACK = {
            "EAGLEVILLE MO": (40.5489, -93.9748),
            "MAYVIEW MO": (39.0148, -93.8260),
            "FORISTELL MO": (38.8285, -90.9332),
            "ST CLAIR MO": (38.3585, -90.9670),
            "JOPLIN MO": (37.0425, -94.5772),
            "CHARLESTON MO": (36.8835, -89.3620),
            "STEELE MO": (36.0848, -89.8322),
            "WILLOW SPRINGS MO": (36.9855, -91.9565),
            "ST GENEVIEVE MO": (37.9542, -90.0988),
            "STE GENEVIEVE MO": (37.9542, -90.0988),
            "WENTZVILLE MO": (38.8256, -90.8752),
            "NEOSHO MO": (36.8322, -94.3755),
            "GRANBY MO": (36.9184, -94.2547),
        }

        df_mapped = ws_df.copy()
        df_mapped['lat_val'] = None
        df_mapped['lon_val'] = None

        has_real_coords = bool(lat_candidates and lon_candidates)
        if has_real_coords:
            df_mapped['lat_val'] = pd.to_numeric(df_mapped[lat_candidates[0]], errors='coerce')
            df_mapped['lon_val'] = pd.to_numeric(df_mapped[lon_candidates[0]], errors='coerce')

        # Koordinatalarni avtomatik to'ldirish
        for idx, row in df_mapped.iterrows():
            if pd.isna(row['lat_val']) or pd.isna(row['lon_val']):
                loc_code = str(row.get('LOCATION', '')).strip().upper()
                loc_desc = str(row.get(name_col, '')).strip().upper()

                if (loc_code, loc_desc) in EXACT_STATIONS:
                    df_mapped.at[idx, 'lat_val'] = EXACT_STATIONS[(loc_code, loc_desc)][0]
                    df_mapped.at[idx, 'lon_val'] = EXACT_STATIONS[(loc_code, loc_desc)][1]
                elif (loc_code, "") in EXACT_STATIONS:
                    df_mapped.at[idx, 'lat_val'] = EXACT_STATIONS[(loc_code, "")][0]
                    df_mapped.at[idx, 'lon_val'] = EXACT_STATIONS[(loc_code, "")][1]
                elif loc_desc in CITY_FALLBACK:
                    df_mapped.at[idx, 'lat_val'] = CITY_FALLBACK[loc_desc][0]
                    df_mapped.at[idx, 'lon_val'] = CITY_FALLBACK[loc_desc][1]
                else:
                    for k, coords in CITY_FALLBACK.items():
                        if k.split()[0] in loc_desc:
                            df_mapped.at[idx, 'lat_val'] = coords[0]
                            df_mapped.at[idx, 'lon_val'] = coords[1]
                            break

        valid_points = df_mapped.dropna(subset=['lat_val', 'lon_val'])
        st.info(f"📍 Xaritada aks ettirilayotgan stansiyalar soni: **{len(valid_points)}** / {len(ws_df)} ta")

        if not valid_points.empty:
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
            st.warning("⚠️ Fayldagi joylashuv nomlari bo'yicha koordinatalar topilmadi.")

# ----------------- 3-BO'LIM: DATA ANALYZER & HIERARCHICAL FILTER -----------------
with tab3:
    st.subheader("📊 Big Data Analyzer: Shtat, County Code Filtr & Universal Tartiblash")

    supported_types = [
        "csv", "tsv", "txt", "tab",
        "xlsx", "xls", "xlsm", "xlsb", "ods",
        "parquet", "feather", "ftr",
        "json", "jsonl", "ndjson",
        "gz", "zip"
    ]

    analysis_file = st.file_uploader(
        "1 mln+ hajmdagi faylni yuklang (CSV, Parquet, Excel, TSV...):", 
        type=supported_types,
        key="big_data_uploader"
    )

    if analysis_file:
        file_name = analysis_file.name.lower()
        try:
            with st.spinner("Katta hajmdagi ma'lumotlar xotiraga yuklanmoqda..."):
                if file_name.endswith('.parquet'):
                    st.session_state["analysis_data"] = pd.read_parquet(analysis_file)
                elif any(file_name.endswith(ext) for ext in ['.feather', '.ftr']):
                    st.session_state["analysis_data"] = pd.read_feather(analysis_file)
                elif any(file_name.endswith(ext) for ext in ['.csv', '.txt', '.gz', '.zip']):
                    # 1 mln qator uchun xotirani tejash optimizatsiyasi
                    st.session_state["analysis_data"] = pd.read_csv(analysis_file, low_memory=False)
                elif any(file_name.endswith(ext) for ext in ['.tsv', '.tab']):
                    st.session_state["analysis_data"] = pd.read_csv(analysis_file, sep='\t', low_memory=False)
                elif file_name.endswith('.json'):
                    st.session_state["analysis_data"] = pd.read_json(analysis_file)
                elif any(file_name.endswith(ext) for ext in ['.xlsx', '.xls', '.xlsm']):
                    xls = pd.ExcelFile(analysis_file)
                    selected_sheet = st.selectbox("Kerakli varaqni tanlang:", xls.sheet_names, key="bd_sheet")
                    st.session_state["analysis_data"] = pd.read_excel(analysis_file, sheet_name=selected_sheet)
        except Exception as e:
            st.error(f"Faylni o'qishda xatolik yuz berdi: {e}")

    df = st.session_state.get("analysis_data")

    if df is not None and not df.empty:
        total_rows = len(df)
        st.success(f"✅ Fayl muvaffaqiyatli yuklandi! Jami ma'lumotlar: **{total_rows:,}** ta qator.")

        working_df = df.copy()

        # 1. Ustunlarni avtomatik aniqlash
        report_col = next((c for c in working_df.columns if any(k in str(c).upper() for k in ['REPORT_NUM', 'REPORT_NUMBER', 'REPORTNO'])), None)
        state_col = next((c for c in working_df.columns if any(k in str(c).upper() for k in ['STATE', 'COUNTY_CODE_STATE', 'ST'])), None)
        county_col = next((c for c in working_df.columns if any(k in str(c).upper() for k in ['COUNTY_CODE', 'COUNTY', 'CNTY'])), None)

        # Agar Police ID mavjud bo'lsa (Report raqamining dastlabki 5 ta belgisi)
        if report_col and 'POLICE_ID' not in working_df.columns:
            working_df.insert(0, 'POLICE_ID', working_df[report_col].astype(str).str.strip().str[:5])

        st.markdown("---")
        st.write("### 🎯 Kaskadli Filtrlash (Shtat ➡️ County Code ➡️ Qidiruv)")

        # Filtrlash paneli
        col_st, col_cc, col_srch = st.columns([1, 1, 1.5])

        # A) Shtat bo'yicha filtr
        selected_state = "Barchasi"
        if state_col:
            with col_st:
                states_list = ["Barchasi"] + sorted(working_df[state_col].dropna().astype(str).unique().tolist())
                selected_state = st.selectbox("1. Shtatni tanlang (State):", states_list)
                if selected_state != "Barchasi":
                    working_df = working_df[working_df[state_col].astype(str) == selected_state]

        # B) County Code bo'yicha dinamik filtr (Tanlangan shtatga qarab moslashadi)
        if county_col:
            with col_cc:
                available_counties = ["Barchasi"] + sorted(working_df[county_col].dropna().astype(str).unique().tolist())
                selected_county = st.selectbox(
                    f"2. County Code ({selected_state} bo'yicha):", 
                    available_counties
                )
                if selected_county != "Barchasi":
                    working_df = working_df[working_df[county_col].astype(str) == selected_county]

        # C) Matnli global qidiruv
        with col_srch:
            global_search = st.text_input("🔍 Matn/Kod bo'yicha qidirish (Road, Police ID, City...):", "")
            if global_search:
                mask = working_df.astype(str).apply(lambda row: row.str.contains(global_search, case=False, na=False)).any(axis=1)
                working_df = working_df[mask]

        st.caption(f"Filtrlangan ma'lumotlar soni: **{len(working_df):,}** ta qator (Jami: {total_rows:,} tadan)")

        # 2. Istalgan shaklda tartiblash (Universal Sort)
        st.markdown("---")
        st.write("### 🔃 Ma'lumotlarni Tartiblash (Sorting)")
        all_cols = working_df.columns.tolist()

        c_s1, c_s2 = st.columns(2)
        with c_s1:
            sort_column = st.selectbox("Tartiblash uchun ustunni tanlang:", ["Asl tartibda"] + all_cols)
        with c_s2:
            sort_direction = st.radio("Tartiblash yo'nalishi:", ["O'sish tartibida (A ➡️ Z, 0 ➡️ 9)", "Kamayish tartibida (Z ➡️ A, 9 ➡️ 0)"], horizontal=True)

        if sort_column != "Asl tartibda":
            is_asc = (sort_direction == "O'sish tartibida (A ➡️ Z, 0 ➡️ 9)")
            working_df = working_df.sort_values(by=sort_column, ascending=is_asc)

        # 3. Filtrlangan va tartiblangan jadvalni ko'rsatish
        st.write("### 📋 Natijaviy Jadval")
        st.dataframe(working_df.head(1000), use_container_width=True)
        if len(working_df) > 1000:
            st.info(f"⚡ Ko'rsatkich tezligi uchun dastlabki 1,000 ta qator ko'rsatildi. Yuklab olish tugmasi orqali **barcha {len(working_df):,} ta** filtrlangan ma'lumot to'liq yuklanadi.")

        # 4. YUKLAB OLISH (CSV & Excel)
        st.markdown("---")
        st.write("### 📥 Saralangan ma'lumotlarni yuklab olish")
        d_col1, d_col2 = st.columns(2)

        with d_col1:
            # Katta hajmdagi ma'lumotlar uchun CSV (1 mln qatorga ham juda tez)
            csv_bytes = working_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Filtrlangan ma'lumotlarni CSV yuklab olish ({len(working_df):,} qator)",
                data=csv_bytes,
                file_name=f"filtered_{selected_state}_data.csv",
                mime="text/csv",
                use_container_width=True
            )

        with d_col2:
            # Excel cheklovi (Excel maksimal 1,048,576 qator oladi)
            if len(working_df) <= 1000000:
                import io
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    working_df.to_excel(writer, index=False, sheet_name='FilteredData')
                st.download_button(
                    label="📥 Natijalarni Excel (.xlsx) yuklab olish",
                    data=excel_buffer.getvalue(),
                    file_name=f"filtered_{selected_state}_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.warning("⚠️ Excel hajmi 1 mln qatordan oshgani sababli CSV formatida yuklab oling.")

    else:
        st.info("👆 Tahlil qilish, shtat va county code bo'yicha filtrlash uchun fayl yuklang.")
