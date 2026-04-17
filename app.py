import streamlit as st
import pandas as pd
import numpy as np
import io
import re

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기")
st.write("발주 시스템 원본 파일 하나만 올리시면, **분할된 모든 표를 병합하고 납품처 앞 숫자를 무시하여** 완벽하게 7열로 추출합니다.")

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

RAW_STORE_MAP = {
    '0903목천물류서비스센터SORTATION': 81020901,
    '0903목천물류서비스센터FLOW': 81020902,
    '0903목천물류서비스센터STOCK': 81020903,
    '0982안성ADC물류센터STOCK': 81020982,
    '0907밀양EXP센터FLOW': 81021903,
    '0967일죽물류서비스센터FLOW': 81021904,
    '0905기흥물류서비스센터FLOW': 81021907,
    '0961밀양물류센터FLOW': 81040912,
    '0961밀양물류센터STOCK': 81040913,
    '0906NEW함안상온물류센터FLOW': 81040912,
    '0906NEW함안상온물류센터SORTATION': 81040913,
    '0906NEW함안상온물류센터SORTER': 81040913,
    '0982안성ADC물류센터SORTATION': 81020980,
    '0982안성ADC물류센터FLOW': 81020981,
    '0970함안EXP물류센터SORTATION': 89029018,
    '0970함안EXP물류센터FLOW': 81040913,
    '0982안성ADC물류센터SINGLE': 81020981,
    '0906NEW함안상온물류센터SINGLE': 81040912,
    '0968365용인DSCDSD': 81040904,
    '0969남양주EXP물류센터FLOW': 81040905,
    '0968365용인DSCSTOCK': 81040904,
    '0969남양주EXP물류센터STOCK': 81040905,
    '0931덕평EXP물류센터FLOW': 81040906,
    '0934오산Exp물류센터FLOW': 81040907,
    '0935오산365물류센터STOCK': 81040908,
    '2001BH)영통점DSD': 81020192,
    '2002BH)강서점DSD': 81020191,
    '2003BH)인천송도점DSD': 81020190,
    '0934오산EXP물류센터SORTATION': 81040907,
    '0907밀양EXP센터SORTATION': 81021903,
    '0905기흥물류서비스센터SORTATION': 81021901,
    '0051강서점DSD': 81020191
}

# [핵심] 앞의 숫자를 모두 없애고 발주코드를 81020000으로 강제 통일하는 로직
NORMALIZED_STORE_MAP = {}
for k, v in RAW_STORE_MAP.items():
    # 문자열 시작 부분의 숫자와 공백을 모두 제거 (예: 0903목천... -> 목천...)
    norm_key = re.sub(r'^[\d\s]+', '', k).upper() 
    NORMALIZED_STORE_MAP[norm_key] = {'발주코드': 81020000, '배송코드': v}

# ==========================================
# 2. 메인 로직
# ==========================================
raw_file = st.file_uploader("발주 원본 엑셀/CSV 파일을 하나만 올려주세요.", type=['xlsx', 'xls', 'csv'])

if raw_file:
    try:
        with st.spinner("모든 주문서를 하나도 빠짐없이 긁어모으는 중입니다..."):
            
            # --- 1. 여러 개로 쪼개진 표(Table) 완벽 병합 로직 (누락 방지) ---
            if raw_file.name.endswith('.csv'):
                try:
                    temp_df = pd.read_csv(raw_file, header=None, encoding='utf-8-sig', errors='ignore')
                except:
                    raw_file.seek(0)
                    temp_df = pd.read_csv(raw_file, header=None, encoding='cp949', errors='ignore')
                
                header_idx = next((i for i, row in temp_df.iterrows() if '상품코드' in row.dropna().astype(str).values), 0)
                raw_file.seek(0)
                try:
                    df_raw = pd.read_csv(raw_file, skiprows=header_idx, encoding='utf-8-sig')
                except:
                    raw_file.seek(0)
                    df_raw = pd.read_csv(raw_file, skiprows=header_idx, encoding='cp949')

            else:
                try:
                    temp_df = pd.read_excel(raw_file, header=None, engine='openpyxl')
                    raw_file.seek(0)
                    header_idx = next((i for i, row in temp_df.iterrows() if '상품코드' in row.dropna().astype(str).values), 0)
                    df_raw = pd.read_excel(raw_file, skiprows=header_idx, engine='openpyxl')
                except:
                    raw_file.seek(0)
                    html_content = raw_file.read()
                    try:
                        tables = pd.read_html(io.BytesIO(html_content), encoding='utf-8')
                    except ValueError:
                        tables = pd.read_html(io.BytesIO(html_content), encoding='cp949')
                    
                    df_list = []
                    for t in tables:
                        mask = t.astype(str).apply(lambda x: x.str.contains('상품코드', na=False)).any(axis=1)
                        if mask.any():
                            h_idx = mask.idxmax()
                            t.columns = t.iloc[h_idx]
                            t = t.iloc[h_idx + 1:]
                            df_list.append(t)
                    
                    if df_list:
                        df_raw = pd.concat(df_list, ignore_index=True)
                    else:
                        raise ValueError("상품코드가 포함된 표를 찾을 수 없습니다.")

            df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]
            if '상품코드' in df_raw.columns:
                df_raw = df_raw[df_raw['상품코드'].astype(str).str.replace(' ', '') != '상품코드']

            cols_to_drop = [c for c in ['TPND', 'TPNB'] if c in df_raw.columns]
            if cols_to_drop:
                df_raw = df_raw.drop(columns=cols_to_drop)

            # --- 2. HYPER_FLOW 강제 변환 ---
            if '입고타입' in df_raw.columns:
                df_raw['입고타입'] = df_raw['입고타입'].astype(str).str.replace('HYPER_FLOW', 'FLOW')

            # --- 3. [핵심] 앞 숫자 제거 후 매칭 로직 ---
            def get_store_info(row):
                store_str = str(row.get('납품처', '')).strip()
                type_str = str(row.get('입고타입', '')).strip().upper()
                
                # 데이터에서도 맨 앞의 숫자와 공백을 날려버림
                clean_store = re.sub(r'^[\d\s]+', '', store_str).upper()
                key = clean_store + type_str
                
                if key in NORMALIZED_STORE_MAP: 
                    return NORMALIZED_STORE_MAP[key]
                elif 'MIX' in type_str: 
                    return NORMALIZED_STORE_MAP.get(clean_store + 'SORTATION', {'발주코드': 81020000, '배송코드': 81040913})
                else: 
                    # 못 찾아도 무조건 발주코드는 81020000 적용
                    return {'발주코드': 81020000, '배송코드': 81040913}

            store_info = df_raw.apply(get_store_info, axis=1, result_type='expand')
            df_raw = pd.concat([df_raw, store_info], axis=1)

            # --- 4. 상품코드 변환 ---
            if '상품코드' in df_raw.columns:
                바코드_숫자 = pd.to_numeric(df_raw['상품코드'], errors='coerce')
                df_raw = df_raw.drop(columns=['상품코드'])
                df_raw['상품코드'] = 바코드_숫자.map(FULL_PRODUCT_MAP)

            # --- 5. 수량 필터링 ---
            df_result = df_raw.rename(columns={'낱개수량': '수량', '낱개당 단가': 'UNIT단가', '발주금액': 'Amount'})
            df_result['수량'] = pd.to_numeric(df_result['수량'], errors='coerce').fillna(0)
            df_result = df_result[df_result['수량'] > 0]

            # --- 6. 그룹핑 ---
            df_result['발주코드'] = df_result['발주코드'].fillna(81020000)
            df_result['배송코드'] = df_result['배송코드'].fillna(81040913)
            df_result = df_result.dropna(subset=['상품코드'])
            
            groupby_cols = ['발주코드', '배송코드', '상품코드', '상품명', 'UNIT단가']
            df_grouped = df_result.groupby(groupby_cols, as_index=False).agg({'수량': 'sum', 'Amount': 'sum'})
            df_grouped = df_grouped.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            # --- 7. 최종 7개 열 생성 ---
            df_final = pd.DataFrame()
            df_final['발주코드'] = df_grouped['발주코드'].astype(int)
            df_final['배송코드'] = df_grouped['배송코드'].astype(int)
            df_final['상품코드'] = df_grouped['상품코드']
            df_final['상품명'] = df_grouped['상품명']
            df_final['수량'] = df_grouped['수량'].astype(int)
            df_final['단가'] = df_grouped['UNIT단가'].astype(int)
            df_final['금액(Amount)'] = df_grouped['Amount'].astype(int)

            st.success(f"✅ 납품처 이름 앞 숫자 무시 및 발주코드 81020000 통일 적용 완료! (총 {len(df_final)}개 데이터 추출)")
            st.dataframe(df_final, hide_index=True)

            # --- 8. 엑셀 다운로드 ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='수주결과')
                
            st.download_button(
                label="📥 최종 수주 파일 다운로드 (Excel)", 
                data=output.getvalue(), 
                file_name="Tesco_최종추출.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"오류 발생: {e}")
