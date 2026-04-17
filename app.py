import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기")
st.write("원본 엑셀 파일 1개만 업로드하면 **사진과 동일한 12열 서식파일 양식**으로 즉시 변환됩니다.")

# ==========================================
# 1. 내장형 마스터 데이터 
# ==========================================
FULL_PRODUCT_MAP = {
    8809020342310: 'ME90521CLA', 8809020342211: 'ME90521CLL', 8809020342419: 'ME90521CLS',
    8809020340804: 'ME90521MC1', 8809020340774: 'ME90521LP2', 8809020348992: 'ME90521E18',
    8809020340279: 'ME90521LR1', 8809020344444: 'ME90521EL9', 8809020344451: 'ME90521EL8',
    8809020344468: 'ME90521EL7', 8809020344192: 'ME90521EL6', 8809020344048: 'ME90521EL4',
    8809020344123: 'ME90521EL0', 8809020344239: 'ME90521E13', 8809020349821: 'ME90521CC4',
    8809020349814: 'ME90521CC2', 8809020349807: 'ME90521CC1', 8809020345212: 'ME00421186',
    8809020345236: 'ME00421183', 8809020345229: 'ME00421301', 8809020348978: 'ME00421151',
    8809020349661: 'ME90621CPS', 8809020349654: 'ME90621CPM', 8809020346516: 'ME90621AT2',
    8809020340286: 'ME00621AB5', 8809020340293: 'ME00621C21', 8809020346561: 'ME00621AT6',
    8809020346585: 'ME90621NA7', 8809020346592: 'ME90621ADI', 8809020346660: 'ME90621A07',
    8809020349425: 'ME00621A08', 8809020349685: 'ME00621AS1', 8809020349692: 'ME00621AL1',
    8809020349708: 'ME00621AR1', 8809020349715: 'ME00621AG1', 8809020349722: 'ME00621AF9',
    8809020349371: 'ME90621GK3', 8809020349418: 'ME90621GK2', 8809020349388: 'ME90621GL3',
    8809020349050: 'ME90621GLO', 8809020349067: 'ME90621GM4', 8809020349074: 'ME90621GE1',
    8809020349203: 'ME90621HCR', 8809020349098: 'ME90621HSL', 8809020349104: 'ME90621SM4',
    8809020349210: 'ME90621SCM', 8809020349166: 'ME90621GO8', 8809020349906: 'ME90621GLL',
    8809020349944: 'ME90621FGC', 8809020340200: 'ME00621H37', 8809020340217: 'ME00621H38',
    8809020340170: 'ME00621C15', 8809020340187: 'ME00621S24', 8809020340194: 'ME00621AS3',
    8809020340606: 'ME00621C22', 8809020340590: 'ME00621H44', 8809020340712: 'ME90621TC1',
    8809020341627: 'ME00621FMC', 8809020341634: 'ME00621FMR', 8809020341641: 'ME00621FBR',
    8809020341207: 'ME80421DR2', 8809020341061: 'ME81921SLL', 8809020341054: 'ME81921SVV',
    8809020341801: 'ME81921SL1', 8809020342501: 'ME90521LD9', 8809020342518: 'ME90521GT2',
    8809020342495: 'ME90521GS2', 8809020349036: 'ME00621CM5', 8809020346509: 'ME90621AFE',
    8809020349968: 'ME00621H41', 8809020342433: 'ME90621AC4', 8809020343478: 'ME00621ABN',
    8809020342525: 'ME80421DCH', 8809020343683: 'ME90521WC4', 8809020343690: 'ME90521WC5',
    8809020343706: 'ME90521WC6', 8809020344338: 'ME00621FHH', 8809020344321: 'ME90621MAM'
}

FULL_STORE_MAP = {
    '0903목천물류서비스센터SORTATION': 81020901, '0903목천물류서비스센터FLOW': 81020902,
    '0903목천물류서비스센터STOCK': 81020903, '0982안성ADC물류센터STOCK': 81020982,
    '0907밀양EXP센터FLOW': 81021903, '0967일죽물류서비스센터FLOW': 81021904,
    '0905기흥물류서비스센터FLOW': 81021907, '0961밀양물류센터FLOW': 81040912,
    '0961밀양물류센터STOCK': 81040913, '0906NEW함안상온물류센터FLOW': 81040912,
    '0906NEW함안상온물류센터SORTATION': 81040913, '0906NEW함안상온물류센터SORTER': 81040913,
    '0968365용인DSCDSD': 81040904, '0969남양주EXP물류센터FLOW': 81040905,
    '0968365용인DSCSTOCK': 81040904, '0969남양주EXP물류센터STOCK': 81040905,
    '0907밀양EXP센터STOCK': 81021903, '0905기흥물류서비스센터STOCK': 81021907,
    '0931덕평EXP물류센터FLOW': 81040906, '0934오산Exp물류센터FLOW': 81040907,
    '0935오산365물류센터STOCK': 81040908, '0982안성ADC물류센터SORTATION': 81020980,
    '0982안성ADC물류센터FLOW': 81020981, '0982안성ADC물류센터SORTER': 81020980,
    '2001BH)영통점DSD': 81020192, '2002BH)강서점DSD': 81020191,
    '2003BH)인천송도점DSD': 81020190, '0934오산EXP물류센터SORTATION': 81040907,
    '0907밀양EXP센터SORTATION': 81021903, '0905기흥물류서비스센터SORTATION': 81021901,
    '0051강서점DSD': 81020191, '0970함안EXP물류센터SORTATION': 89029018,
    '0970함안EXP물류센터FLOW': 81040913, '0982안성ADC물류센터SINGLE': 81020981,
    '0906NEW함안상온물류센터SINGLE': 81040912
}

# ==========================================
# 2. 메인 화면: 원본 데이터 업로드
# ==========================================
raw_file = st.file_uploader("발주 원본 파일 하나만 올려주세요. (자동 헤더 인식 적용됨)", type=['xlsx', 'xls', 'csv'])

if raw_file:
    try:
        with st.spinner("요청하신 규칙(HYPER_FLOW 변환 등)을 적용하여 양식을 만드는 중입니다..."):
            
            # --- [Step 1] 똑똑한 데이터 로드 (헤더 찾기) ---
            if raw_file.name.endswith('.csv'):
                temp_df = pd.read_csv(raw_file, header=None, encoding='utf-8-sig', errors='ignore')
                raw_file.seek(0)
                header_idx = next((i for i, row in temp_df.iterrows() if '상품코드' in row.dropna().astype(str).values), 0)
                df_raw = pd.read_csv(raw_file, skiprows=header_idx)
            else:
                try:
                    temp_df = pd.read_excel(raw_file, header=None, engine='openpyxl')
                    raw_file.seek(0)
                    header_idx = next((i for i, row in temp_df.iterrows() if '상품코드' in row.dropna().astype(str).values), 0)
                    df_raw = pd.read_excel(raw_file, skiprows=header_idx, engine='openpyxl')
                except:
                    raw_file.seek(0)
                    df_raw = pd.read_html(raw_file)[0]
                    header_idx = df_raw[df_raw.eq('상품코드').any(axis=1)].index[0]
                    df_raw.columns = df_raw.iloc[header_idx]
                    df_raw = df_raw[header_idx + 1:]

            df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]

            # TPND, TPNB 컬럼 삭제
            cols_to_drop = [c for c in ['TPND', 'TPNB'] if c in df_raw.columns]
            if cols_to_drop:
                df_raw = df_raw.drop(columns=cols_to_drop)

            # ★ [요청사항 1] HYPER_FLOW를 FLOW로 강제 일괄 변환 ★
            if '입고타입' in df_raw.columns:
                df_raw['입고타입'] = df_raw['입고타입'].astype(str).str.replace('HYPER_FLOW', 'FLOW')

            # --- [Step 2] 배송코드 추출 ---
            def get_delivery_code(store, in_type):
                store_str, type_str = str(store).strip(), str(in_type).strip()
                raw_key = (store_str + type_str).replace(" ", "")
                
                # 이미 위에서 HYPER_FLOW를 FLOW로 바꿨으므로 여기서 바로 매칭됩니다.
                if raw_key in FULL_STORE_MAP: return FULL_STORE_MAP[raw_key]
                if 'MIX' in type_str: return FULL_STORE_MAP.get((store_str + 'SORTATION').replace(" ", ""), 81040913)
                return FULL_STORE_MAP.get(raw_key, 81040913)

            df_raw['배송코드'] = df_raw.apply(lambda r: get_delivery_code(r['납품처'], r['입고타입']), axis=1)

            # --- [Step 3] 상품코드 변환 ---
            if '상품코드' in df_raw.columns:
                바코드_숫자 = pd.to_numeric(df_raw['상품코드'], errors='coerce')
                df_raw = df_raw.drop(columns=['상품코드'])
                df_raw['상품코드'] = 바코드_숫자.map(FULL_PRODUCT_MAP)
            else:
                df_raw['상품코드'] = np.nan

            # --- [Step 4] 필요한 열만 뽑아서 수량 0 제거 ---
            df_result = df_raw.rename(columns={'낱개수량': '수량', '낱개당 단가': 'UNIT단가', '발주금액': 'Amount'})
            df_result['수량'] = pd.to_numeric(df_result['수량'], errors='coerce').fillna(0)
            df_result = df_result[df_result['수량'] > 0]

            # --- [Step 5] 동일 배송코드 + 상품코드 합산 (그룹핑) ---
            groupby_cols = ['배송코드', '상품코드', '상품명', 'UNIT단가']
            df_grouped = df_result.groupby(groupby_cols, as_index=False).agg({'수량': 'sum', 'Amount': 'sum'})
            df_grouped = df_grouped.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            # --- [Step 6] ★ 서식파일과 100% 동일한 12열 양식으로 재배치 ★ ---
            df_final = pd.DataFrame()
            df_final['발주처코드(EDI)'] = 133
            df_final['배송코드(EDI)'] = np.nan
            df_final['상품코드'] = np.nan  
            df_final['Sum Code'] = np.nan
            
            # ★ [요청사항 2] 발주코드 8102000 고정 ★ (기존 81020000에서 수정)
            df_final['발주코드'] = 8102000
            
            df_final['배송코드'] = df_grouped['배송코드'].astype(int)
            df_final['상품코드.1'] = df_grouped['상품코드']  
            df_final['상품명'] = df_grouped['상품명']
            df_final['UNIT수량'] = df_grouped['수량'].astype(int)
            df_final['UNIT단가'] = df_grouped['UNIT단가'].astype(int)
            df_final['금       액'] = df_grouped['Amount'].astype(int)
            df_final['부  가   세'] = 0

            st.success("✅ HYPER_FLOW 강제 변환 및 발주코드(8102000) 고정 적용 완료!")
            st.dataframe(df_final)

            # --- [Step 7] 엑셀 다운로드 ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='서식파일')
            
            st.download_button(
                label="📥 테스코 서식파일 양식 다운로드 (Excel)", 
                data=output.getvalue(), 
                file_name="Tesco_업로드용_서식파일.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"오류 발생: {e}")
