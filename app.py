import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기")
st.warning("⚠️ 주의: 화면의 표를 마우스로 드래그해서 복사하면 글자가 뭉개집니다! 반드시 맨 아래의 **[엑셀 다운로드]** 버튼을 눌러주세요.")

# ==========================================
# 1. 마스터 데이터 (상품 및 발주처 상세 매핑)
# ==========================================
PRODUCT_MAP = {
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
# 2. 메인 화면: 원본 데이터 업로드
# ==========================================
raw_file = st.file_uploader("발주 원본 파일 하나만 올려주세요.", type=['xlsx', 'xls', 'csv'])

if raw_file:
    try:
        with st.spinner("데이터를 처리 중입니다..."):
            
            # --- [Step 1] 데이터 로드 및 헤더 인식 ---
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
            
            # [규칙 1] HYPER_FLOW -> FLOW 변환
            if '입고타입' in df_raw.columns:
                df_raw['입고타입'] = df_raw['입고타입'].astype(str).str.replace('HYPER_FLOW', 'FLOW')

            # --- [Step 2] VLOOKUP 매핑 로직 ---
            def get_store_info(row):
                store_str = str(row.get('납품처', '')).strip()
                type_str = str(row.get('입고타입', '')).strip()
                key = (store_str + type_str).replace(" ", "")
                default = {'EDI': 133, '발주코드': 81020000, '배송코드': 81040913}
                return STORE_DETAIL_MAP.get(key, default)

            store_info = df_raw.apply(get_store_info, axis=1, result_type='expand')
            df_raw = pd.concat([df_raw, store_info], axis=1)

            # --- [Step 3] 상품코드 변환 ---
            if '상품코드' in df_raw.columns:
                바코드_숫자 = pd.to_numeric(df_raw['상품코드'], errors='coerce')
                df_raw = df_raw.drop(columns=['상품코드'])
                df_raw['상품코드'] = 바코드_숫자.map(PRODUCT_MAP)
            else:
                df_raw['상품코드'] = np.nan

            # --- [Step 4] 데이터 정제 및 그룹핑 ---
            df_result = df_raw.rename(columns={'낱개수량': '수량', '낱개당 단가': 'UNIT단가', '발주금액': 'Amount'})
            df_result['수량'] = pd.to_numeric(df_result['수량'], errors='coerce').fillna(0)
            df_result = df_result[df_result['수량'] > 0]

            # 배송코드와 상품코드가 모두 동일한 경우 합산
            groupby_cols = ['EDI', '발주코드', '배송코드', '상품코드', '상품명', 'UNIT단가']
            df_grouped = df_result.groupby(groupby_cols, as_index=False).agg({'수량': 'sum', 'Amount': 'sum'})
            df_grouped = df_grouped.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            # --- [Step 5] 서식파일 12열 양식 구성 ---
            df_final = pd.DataFrame()
            df_final['발주처코드(EDI)'] = df_grouped['EDI']
            df_final['배송코드(EDI)'] = np.nan
            df_final['상품코드'] = np.nan
            df_final['Sum Code'] = np.nan
            df_final['발주코드'] = df_grouped['발주코드']
            df_final['배송코드'] = df_grouped['배송코드'].astype(int)
            df_final['상품코드_리얼'] = df_grouped['상품코드']  # 임시 이름
            df_final['상품명'] = df_grouped['상품명']
            df_final['UNIT수량'] = df_grouped['수량'].astype(int)
            df_final['UNIT단가'] = df_grouped['UNIT단가'].astype(int)
            df_final['금       액'] = df_grouped['Amount'].astype(int)
            df_final['부  가   세'] = (df_final['금       액'] * 0.1).astype(int)

            # ★ [중요] 사진과 완벽히 똑같이 열 이름 맞추기 (상품코드 중복 허용) ★
            df_final.columns = [
                '발주처코드(EDI)', '배송코드(EDI)', '상품코드', 'Sum Code', 
                '발주코드', '배송코드', '상품코드', '상품명', 
                'UNIT수량', 'UNIT단가', '금       액', '부  가   세'
            ]

            st.success("✅ 처리가 완료되었습니다! **꼭 아래 버튼을 눌러 엑셀 파일을 다운로드하세요.**")
            
            # 행 번호(Index) 숨겨서 깔끔하게 보여주기
            st.dataframe(df_final, hide_index=True)

            # --- [Step 6] 엑셀 다운로드 ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='서식파일')
            
            st.download_button(
                label="📥 최종 수주 파일 다운로드 (Excel)", 
                data=output.getvalue(), 
                file_name="Tesco_최종업로드양식.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"오류 발생: {e}")
