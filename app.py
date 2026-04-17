import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기 (핵심 7열 추출본)")
st.write("원본 엑셀 파일 1개만 올리시면, 마스터 매핑 및 수량 합산을 거쳐 **필요한 핵심 7개 열**만 깔끔하게 뽑아줍니다.")

# ==========================================
# 1. 마스터 데이터 세팅
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

STORE_DETAIL_MAP = {
    '0903목천물류서비스센터SORTATION': {'EDI': 133, '발주코드': 81020000, '배송코드': 81020901},
    '0903목천물류서비스센터FLOW': {'EDI': 622, '발주코드': 81021000, '배송코드': 81020902},
    '0903목천물류서비스센터STOCK': {'EDI': 622, '발주코드': 81021000, '배송코드': 81020903},
    '0982안성ADC물류센터STOCK': {'EDI': 622, '발주코드': 81021000, '배송코드': 81020982},
    '0907밀양EXP센터FLOW': {'EDI': 622, '발주코드': 81021000, '배송코드': 81021903},
    '0967일죽물류서비스센터FLOW': {'EDI': 622, '발주코드': 81021000, '배송코드': 81021904},
    '0905기흥물류서비스센터FLOW': {'EDI': 622, '발주코드': 81021000, '배송코드': 81021907},
    '0961밀양물류센터FLOW': {'EDI': 622, '발주코드': 81021000, '배송코드': 81040912},
    '0961밀양물류센터STOCK': {'EDI': 622, '발주코드': 81021000, '배송코드': 81040913},
    '0906NEW함안상온물류센터FLOW': {'EDI': 622, '발주코드': 81021000, '배송코드': 81040912},
    '0906NEW함안상온물류센터SORTATION': {'EDI': 622, '발주코드': 81021000, '배송코드': 81040913},
    '0906NEW함안상온물류센터SORTER': {'EDI': 622, '발주코드': 81021000, '배송코드': 81040913},
    '0982안성ADC물류센터SORTATION': {'EDI': 622, '발주코드': 81021000, '배송코드': 81020980},
    '0982안성ADC물류센터FLOW': {'EDI': 622, '발주코드': 81021000, '배송코드': 81020981},
    '0970함안EXP물류센터SORTATION': {'EDI': 622, '발주코드': 81021000, '배송코드': 89029018},
    '0970함안EXP물류센터FLOW': {'EDI': 622, '발주코드': 81021000, '배송코드': 81040913},
    '0982안성ADC물류센터SINGLE': {'EDI': 622, '발주코드': 81021000, '배송코드': 81020981},
    '0906NEW함안상온물류센터SINGLE': {'EDI': 622, '발주코드': 81021000, '배송코드': 81040912}
}

# ==========================================
# 2. 메인 로직
# ==========================================
raw_file = st.file_uploader("발주 원본 파일 1개만 올려주세요.", type=['xlsx', 'xls', 'csv'])

if raw_file:
    try:
        with st.spinner("데이터 정제 및 그룹핑 중..."):
            
            # --- 1. 똑똑하게 헤더 찾아 데이터 로드 ---
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
            
            # --- 2. HYPER_FLOW 강제 변환 ---
            if '입고타입' in df_raw.columns:
                df_raw['입고타입'] = df_raw['입고타입'].astype(str).str.replace('HYPER_FLOW', 'FLOW')

            # --- 3. 배송처 및 발주코드 매핑 (VLOOKUP) ---
            def get_store_info(row):
                store_str = str(row.get('납품처', '')).strip()
                type_str = str(row.get('입고타입', '')).strip()
                key = (store_str + type_str).replace(" ", "")
                return STORE_DETAIL_MAP.get(key, {'EDI': 133, '발주코드': 81020000, '배송코드': 81040913})

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

            # --- 6. 그룹핑 (동일 발주코드+배송코드+상품코드 시 합산) ---
            groupby_cols = ['발주코드', '배송코드', '상품코드', '상품명', 'UNIT단가']
            df_grouped = df_result.groupby(groupby_cols, as_index=False).agg({'수량': 'sum', 'Amount': 'sum'})
            df_grouped = df_grouped.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            # --- 7. ★ 깔끔한 7개 열 최종본 구성 ★ ---
            df_final = pd.DataFrame()
            df_final['발주코드'] = df_grouped['발주코드']
            df_final['배송코드'] = df_grouped['배송코드'].astype(int)
            df_final['상품코드'] = df_grouped['상품코드']
            df_final['상품명'] = df_grouped['상품명']
            df_final['수량'] = df_grouped['수량'].astype(int)
            df_final['단가'] = df_grouped['UNIT단가'].astype(int)
            df_final['금액(Amount)'] = df_grouped['Amount'].astype(int)

            st.success("✅ 불필요한 열을 제거하고 요청하신 **7개 핵심 열**만 완벽하게 추출했습니다!")
            
            # 웹 화면에 보기 좋게 출력
            st.dataframe(df_final, hide_index=True)

            # --- 8. 엑셀 다운로드 ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='수주결과')
                
            st.download_button(
                label="📥 핵심 7열 수주 파일 다운로드 (Excel)", 
                data=output.getvalue(), 
                file_name="Tesco_최종추출.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"오류 발생: {e}")
