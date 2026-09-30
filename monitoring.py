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

# ----------------- 3-BO'LIM: DATA ANALYZER & GEMINI (LIMITSIZ & POLICE ID ANALYZER) -----------------
with tab3:
    st.subheader("📊 Data Analyzer & Police Report ID Tahlili (Cheklovlarsiz)")

    supported_types = [
        "csv", "tsv", "txt", "tab",
        "xlsx", "xls", "xlsm", "xlsb", "ods",
        "parquet", "feather", "ftr",
        "json", "jsonl", "ndjson",
        "gz", "zip"
    ]

    analysis_file = st.file_uploader(
        "Tahlil qilinadigan faylni yuklang (CSV, Excel, Parquet...):", 
        type=supported_types,
        key="analysis_uploader_unlimited"
    )

    if analysis_file:
        file_name = analysis_file.name.lower()
        try:
            with st.spinner("Barcha ma'lumotlar to'liq o'qilmoqda..."):
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
                    selected_sheet = st.selectbox("Kerakli varaqni tanlang:", xls.sheet_names, key="analysis_sheet_unl")
                    st.session_state["analysis_data"] = pd.read_excel(analysis_file, sheet_name=selected_sheet)
        except Exception as e:
            st.error(f"Faylni o'qishda xatolik: {e}")

    df = st.session_state.get("analysis_data")

    if df is not None and not df.empty:
        total_rows = len(df)
        st.success(f"✅ Fayl 100% to'liq yuklandi! Jami qatorlar soni: **{total_rows:,}** ta (Hech qanday limitsiz ishlamoqda)")

        # 1. REPORT_NUMBER ustunini topish va Police ID ustunini yasash
        report_col = next((c for c in df.columns if any(k in str(c).upper() for k in ['REPORT_NUM', 'REPORT_NUMBER', 'REPORTNO', 'REPORT_NO'])), None)

        working_df = df.copy()

        if report_col:
            # Dastlabki 5 raqamni Police ID qilib ajratish
            working_df['POLICE_ID (Bosh 5)'] = working_df[report_col].astype(str).str.strip().str[:5]
            # 5 tadan keyingi qolgan qismi
            working_df['REPORT_REST'] = working_df[report_col].astype(str).str.strip().str[5:]

            st.write("### 🔍 Police ID (Boshidagi 5 raqam) bo'yicha saralash va filtr")

            # Police ID larning umumiy takrorlanishlar sonini hisoblash
            police_counts = (
                working_df['POLICE_ID (Bosh 5)']
                .value_counts()
                .reset_index()
            )
            police_counts.columns = ['POLICE_ID', 'Jami_takrorlar_soni']

            c_f1, c_f2 = st.columns([1, 2])
            with c_f1:
                manual_id = st.text_input("Police ID (5 ta raqam) qo'lda qidirish:", placeholder="Masalan: 70350")
            
            with c_f2:
                # Variantlar ko'rinishi: "70350 (2,450 ta report)"
                police_options = [
                    f"{row['POLICE_ID']}  —  ({row['Jami_takrorlar_soni']:,} ta report)"
                    for _, row in police_counts.iterrows()
                ]
                selected_police_labels = st.multiselect(
                    "Yoki eng ko'p uchragan Police ID'lardan tanlang (takrorlanish soni bilan):",
                    options=police_options,
                    default=[]
                )

            # Tanlangan Police ID lar bo'yicha butun bazani filtrlash
            if manual_id:
                working_df = working_df[working_df['POLICE_ID (Bosh 5)'].str.startswith(manual_id)]
                st.info(f"Police ID `{manual_id}` bo'yicha **{len(working_df):,}** ta yozuv topildi.")
            elif selected_police_labels:
                selected_ids = [label.split(" ")[0].strip() for label in selected_police_labels]
                working_df = working_df[working_df['POLICE_ID (Bosh 5)'].isin(selected_ids)]
                st.info(f"Tanlangan Police ID'lar bo'yicha jami **{len(working_df):,}** ta yozuv saralandi.")
        else:
            st.warning("⚠️ Jadvalda `REPORT_NUMBER` nomli ustun topilmadi.")

        st.markdown("---")
        st.write(f"### 📋 Tahlil qilinayotgan ma'lumotlar bazasi ({len(working_df):,} ta qator)")
        st.dataframe(working_df.head(20), use_container_width=True)

        # 2. Bog'liqliklar uchun ustunlarni belgilash
        st.write("### 📌 Bog'liqliklar va Qoliplarni aniqlash ustunlari")
        all_cols = working_df.columns.tolist()

        # Dastlabki ustunlarni avtomatik belgilash
        default_cols = [c for c in ['ROAD', 'LOCATION_DESC', 'COUNTY_CODE_STATE', 'COUNTY_CODE', 'POLICE_ID (Bosh 5)', report_col] if c and c in all_cols]

        selected_columns = st.multiselect(
            "Qoliplarni aniqlash ustunlarini tanlang:",
            options=all_cols,
            default=default_cols
        )

        if len(selected_columns) >= 2:
            # NO LIMIT: Barcha kiritilgan ma'lumotlar asosida to'liq guruhlash va saralash
            with st.spinner("Barcha qatorlar bo'yicha noyob qoliplar chiqarilmoqda..."):
                patterns = (
                    working_df
                    .groupby(selected_columns, dropna=False)
                    .size()
                    .reset_index(name='Takrorlanish_soni')
                )
                patterns = patterns.sort_values(by='Takrorlanish_soni', ascending=False)

            st.write(f"### 🎯 Ajratib olingan noyob qoliplar ({len(patterns):,} ta pattern)")
            st.dataframe(patterns, use_container_width=True)

            # Excel va CSV ga yuklab olish
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    label="📥 Natijalarni CSV formatida yuklab olish",
                    data=patterns.to_csv(index=False).encode('utf-8'),
                    file_name="police_patterns_unlimited.csv",
                    mime="text/csv"
                )
            with col_d2:
                import io
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='openpyxl') as wr:
                    patterns.to_excel(wr, index=False, sheet_name='Patterns')
                st.download_button(
                    label="📥 Natijalarni Excel (.xlsx) formatida yuklab olish",
                    data=out.getvalue(),
                    file_name="police_patterns_unlimited.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Gemini AI tahlili
            if st.button("🤖 Gemini orqali mantiqiy qoidalarni chiqarish"):
                if not api_key:
                    st.error("Iltimos, chap tarafdagi maydonga Gemini API kalitingizni kiriting!")
                else:
                    client = genai.Client(api_key=api_key)
                    sample_data = patterns.head(50).to_string(index=False)
                    prompt = f"""
                    Quyidagi transport tekshiruvi (Police inspection patterns) qonuniyatlarini tahlil qil.
                    Ustunlar: {', '.join(selected_columns)}
                    
                    Qaysi Police ID qaysi yo'llar (ROAD), joylashuvlar (LOCATION_DESC) va okruglarga (COUNTY_CODE) birikkanini aniqla va qat'iy mantiqiy qoidalar ro'yxatini chiqarib ber:
                    Format:
                    IF POLICE_ID=... AND ROAD=... THEN LOCATION_DESC=... (COUNTY_CODE=...)
                    
                    Ma'lumotlar namunasi:
                    {sample_data}
                    """
                    with st.spinner("Gemini tahlil qilmoqda..."):
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt,
                        )
                        st.write("### 🧠 Aniqlangan mantiqiy qoidalar:")
                        st.markdown(response.text)
        else:
            st.warning("Iltimos, guruhlash uchun kamida 2 ta ustunni tanlang.")
