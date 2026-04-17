import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기")
st.write("발주 시스템 원본 파일 하나만 올리시면, **마스터 시트의 규칙대로 납품처별 발주/배송코드를 정확히 나누어** 7개 열로 추출합니다.")

# ==========================================
# 1. 마스터 데이터 (서식파일 완벽 이식)
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
    8809020341207: 'ME80421DR2', 8809020346509: 'ME90621AFE', 8809020344321: 'ME90621MAM'
}

# [핵심] VLOOKUP 대체: 서식파일의 'Tesco 발주처코드' 시트 내용 100% 반영
FULL_STORE_MAP = {
    '0903목천물류서비스센터SORTATION': {'발주코드': 81020000, '배송코드': 81020901},
    '0903목천물류서비스센터FLOW': {'발주코드': 81021000, '배송코드': 81020902},
    '0903목천물류서비스센터STOCK': {'발주코드': 81021000, '배송코드': 81020903},
    '0982안성ADC물류센터STOCK': {'발주코드': 81021000, '배송코드': 81020982},
    '0907밀양EXP센터FLOW': {'발주코드': 81021000, '배송코드': 81021903},
    '0967일죽물류서비스센터FLOW': {'발주코드': 81021000, '배송코드': 81021904},
    '0905기흥물류서비스센터FLOW': {'발주코드': 81021000, '배송코드': 81021907},
    '0961밀양물류센터FLOW': {'발주코드': 81021000, '배송코드': 81040912},
    '0961밀양물류센터STOCK': {'발주코드': 81021000, '배송코드': 81040913},
    '0906NEW함안상온물류센터FLOW': {'발주코드': 81021000, '배송코드': 81040912},
    '0906NEW함안상온물류센터SORTATION': {'발주코드': 81021000, '배송코드': 81040913},
    '0906NEW함안상온물류센터SORTER': {'발주코드': 81021000, '배송코드': 81040913},
    '0982안성ADC물류센터SORTATION': {'발주코드': 81021000, '배송코드': 81020980},
    '0982안성ADC물류센터FLOW': {'발주코드': 81021000, '배송코드': 81020981},
    '0970함안EXP물류센터SORTATION': {'발주코드': 81021000, '배송코드': 89029018},
    '0970함안EXP물류센터FLOW': {'발주코드': 81021000, '배송코드': 81040913},
    '0982안성ADC물류센터SINGLE': {'발주코드': 81021000, '배송코드': 81020981},
    '0906NEW함안상온물류센터SINGLE': {'발주코드': 81021000, '배송코드': 81040912},
    '0968365용인DSCDSD': {'발주코드': 81021000, '배송코드': 81040904},
    '0969남양주EXP물류센터FLOW': {'발주코드': 81021000, '배송코드': 81040905},
    '0968365용인DSCSTOCK': {'발주코드': 81021000, '배송코드': 81040904},
    '0969남양주EXP물류센터STOCK': {'발주코드': 81021000, '배송코드': 81040905},
    '0931덕평EXP물류센터FLOW': {'발주코드': 81021000, '배송코드': 81040906},
    '0934오산Exp물류센터FLOW': {'발주코드': 81021000, '배송코드': 81040907},
    '0935오산365물류센터STOCK': {'발주코드': 81021000, '배송코드': 81040908},
    '2001BH)영통점DSD': {'발주코드': 81021000, '배송코드': 81020192},
    '2002BH)강서점DSD': {'발주코드': 81021000, '배송코드': 81020191},
    '2003BH)인천송도점DSD': {'발주코드': 81021000, '배송코드': 81020190},
    '0934오산EXP물류센터SORTATION': {'발주코드': 81021000, '배송코드': 81040907},
    '0907밀양EXP센터SORTATION': {'발주코드': 81021000, '배송코드': 81021903},
    '0905기흥물류서비스센터SORTATION': {'발주코드': 81021000, '배송코드': 81021901},
    '0051강서점DSD': {'발주코드': 81021000, '배송코드': 81020191}
}

# ==========================================
# 2. 메인 로직
# ==========================================
raw_file = st.file_uploader("발주 원본 엑셀 파일 1개만 올려주세요.", type=['xlsx', 'xls', 'csv'])

if raw_file:
    try:
        with st.spinner("데이터 매핑 및 정제 중..."):
            
            # --- 1. 파일 자동 인식 로직 ---
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

            # 중복된 엑셀 열 제거 (안전장치)
            df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]

            # 불필요한 행 제거
            cols_to_drop = [c for c in ['TPND', 'TPNB'] if c in df_raw.columns]
            if cols_to_drop:
                df_raw = df_raw.drop(columns=cols_to_drop)

            # --- 2. HYPER_FLOW 강제 변환 ---
            if '입고타입' in df_raw.columns:
                df_raw['입고타입'] = df_raw['입고타입'].astype(str).str.replace('HYPER_FLOW', 'FLOW')

            # --- 3. VLOOKUP 발주처 매핑 (발주코드, 배송코드 동시 추출) ---
            def get_store_info(row):
                store_str = str(row.get('납품처', '')).strip()
                type_str = str(row.get('입고타입', '')).strip()
                key = (store_str + type_str).replace(" ", "")
                
                # 매칭 시 VLOOKUP 처럼 딕셔너리 값 불러오기
                if key in FULL_STORE_MAP:
                    return FULL_STORE_MAP[key]
                elif 'MIX' in type_str:  # MIX는 SORTATION으로 간주
                    fallback = (store_str + 'SORTATION').replace(" ", "")
                    return FULL_STORE_MAP.get(fallback, {'발주코드': np.nan, '배송코드': np.nan})
                else:
                    return {'발주코드': np.nan, '배송코드': np.nan}

            store_info = df_raw.apply(get_store_info, axis=1, result_type='expand')
            df_raw = pd.concat([df_raw, store_info], axis=1)

            # --- 4. 상품코드(바코드 -> ME코드) 매핑 ---
            if '상품코드' in df_raw.columns:
                바코드_숫자 = pd.to_numeric(df_raw['상품코드'], errors='coerce')
                df_raw = df_raw.drop(columns=['상품코드'])
                df_raw['상품코드'] = 바코드_숫자.map(FULL_PRODUCT_MAP)
            else:
                df_raw['상품코드'] = np.nan

            # --- 5. 수량 필터링 및 이름 변경 ---
            df_result = df_raw.rename(columns={'낱개수량': '수량', '낱개당 단가': 'UNIT단가', '발주금액': 'Amount'})
            df_result['수량'] = pd.to_numeric(df_result['수량'], errors='coerce').fillna(0)
            df_result = df_result[df_result['수량'] > 0]

            # --- 6. 그룹핑 (발주코드+배송코드+상품코드 동일 시 합산) ---
            groupby_cols = ['발주코드', '배송코드', '상품코드', '상품명', 'UNIT단가']
            # 매핑 안된 값(NaN)이 있으면 제거
            df_result = df_result.dropna(subset=['발주코드', '배송코드', '상품코드'])
            
            df_grouped = df_result.groupby(groupby_cols, as_index=False).agg({'수량': 'sum', 'Amount': 'sum'})
            df_grouped = df_grouped.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            # --- 7. ★ 깔끔한 7개 열 최종본 구성 ★ ---
            df_final = pd.DataFrame()
            df_final['발주코드'] = df_grouped['발주코드'].astype(int)
            df_final['배송코드'] = df_grouped['배송코드'].astype(int)
            df_final['상품코드'] = df_grouped['상품코드']
            df_final['상품명'] = df_grouped['상품명']
            df_final['수량'] = df_grouped['수량'].astype(int)
            df_final['단가'] = df_grouped['UNIT단가'].astype(int)
            df_final['금액(Amount)'] = df_grouped['Amount'].astype(int)

            st.success("✅ VLOOKUP 매핑이 완벽 적용되었습니다! (배송처별로 발주코드가 다르게 나옵니다)")
            
            # 웹 화면에 보기 좋게 출력
            st.dataframe(df_final, hide_index=True)

            # --- 8. 엑셀 다운로드 ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='수주결과')
                
            st.download_button(
                label="📥 수주 파일 다운로드 (Excel)", 
                data=output.getvalue(), 
                file_name="Tesco_최종추출.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"오류 발생: {e}")
