import streamlit as st
import pandas as pd
from google import genai

st.set_page_config(page_title="Safety Pattern Finder", layout="wide")
st.title("Safety Data — Qonuniyatlar va qoidalarni aniqlash ilovasi")

# Yon paneldan Gemini API kalitini kiritish
api_key = st.sidebar.text_input("Gemini API kalitini kiriting:", type="password")

# Fayl yuklash maydoni
uploaded_file = st.file_uploader("Katta hajmdagi faylni yuklang (CSV yoki Excel)", type=["csv", "xlsx", "xls"])

if uploaded_file:
    st.info("Fayl tahlil qilinmoqda...")
    
    df = None
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        # Excel varaqlari ro'yxatini olish
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        selected_sheet = st.selectbox("Kerakli varaqni (Sheet) tanlang:", sheet_names)
        
        # Tanlangan varaqni o'qish
        with st.spinner("Jadval yuklanmoqda..."):
            df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

    if df is not None and not df.empty:
        st.success(f"Fayl muvaffaqiyatli yuklandi! Jami qatorlar soni: {len(df):,}")
        
        st.subheader("1. Ma'lumotlardan namuna")
        st.dataframe(df.head(10))
        
        # Ustunlarni avtomatik aniqlash yoki foydalanuvchiga tanlash imkonini berish
        st.subheader("2. Tahlil qilish uchun ustunlarni belgilang:")
        all_columns = df.columns.tolist()
        
        selected_columns = st.multiselect(
            "Tahlil qilinadigan ustunlarni tanlang (masalan: County, Location, Facility, Address):",
            options=all_columns,
            default=[col for col in all_columns if any(k in str(col).lower() for k in ['county', 'location', 'facil', 'address', 'site', 'hwy', 'road'])][:4]
        )
        
        if len(selected_columns) >= 2:
            # Noyob qoliplarni chiqarish
            patterns = df.groupby(selected_columns, dropna=False).size().reset_index(name='Takrorlanish_soni')
            patterns = patterns.sort_values(by='Takrorlanish_soni', ascending=False)
            
            st.subheader(f"3. Ajratib olingan noyob qoliplar ({len(patterns):,} ta pattern)")
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
                    
                    Qaysi parametrlar qaysi manzil yoki xususiyatga to'g'ri kelishini aniqla va qat'iy mantiqiy qoidalar ro'yxatini tuzib ber:
                    Format:
                    IF {selected_columns[0]}=... AND {selected_columns[1]}=... THEN ...
                    
                    Qoliplar namunasi:
                    {sample_data}
                    """
                    
                    with st.spinner("Gemini qonuniyatlarni o'rganmoqda..."):
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt,
                        )
                        st.subheader("4. Aniqlangan mantiqiy qoidalar:")
                        st.markdown(response.text)
        else:
            st.warning("Iltimos, yuqoridagi ro'yxatdan kamida 2 ta ustunni tanlang.")
    else:
        st.error("Tanlangan varaq bo'sh yoki ma'lumotlarni o'qib bo'lmadi. Boshqa varaqni tanlab ko'ring.")
