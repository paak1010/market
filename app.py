import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기 (최종 Excel 버전)")
st.write("""
원본 데이터(ordview_...) 파일만 업로드하면, 기준 정보(상품코드, 배송코드 등)를 
자동으로 매핑하고 **동일 배송처/상품의 수량을 합산하여 엑셀(.xlsx) 파일로** 만들어줍니다.
""")

# ==========================================
# 1. 사이드바: 마스터 데이터 세팅
# ==========================================
st.sidebar.header("⚙️ 기초 마스터 데이터")
st.sidebar.info("""
기준 정보 파일은 매번 업로드할 필요 없이 
앱과 같은 폴더에 아래 이름으로 저장해두면 자동으로 불러옵니다.
- 상품코드.csv
- Tesco 발주처코드.csv
""")

# 기본 파일 경로
master_prod_path = '상품코드.csv'
master_store_path = 'Tesco 발주처코드.csv'

# 혹시 파일이 폴더에 없을 경우를 대비한 수동 업로드 창
upload_prod = st.sidebar.file_uploader("상품코드 마스터 수동 업로드 (선택)", type=['csv'])
upload_store = st.sidebar.file_uploader("발주처코드 마스터 수동 업로드 (선택)", type=['csv'])

df_prod = None
df_store = None

try:
    if upload_prod:
        df_prod = pd.read_csv(upload_prod)
    else:
        df_prod = pd.read_csv(master_prod_path)
        
    if upload_store:
        df_store = pd.read_csv(upload_store)
    else:
        df_store = pd.read_csv(master_store_path)
        
    st.sidebar.success("✅ 마스터 데이터 로드 완료")
except FileNotFoundError:
    st.sidebar.error("⚠️ 폴더에 마스터 파일이 없습니다. 사이드바에서 직접 업로드하거나 앱 폴더에 파일을 넣어주세요.")
    st.stop() # 마스터 데이터가 없으면 앱 구동 중지

# ==========================================
# 2. 메인 화면: 원본 데이터 업로드 및 처리
# ==========================================
st.header("📂 오늘의 원본 데이터 업로드")
file_raw = st.file_uploader("발주 시스템에서 다운받은 원본 데이터(csv)를 올려주세요.", type=['csv'])

if file_raw:
    try:
        with st.spinner("데이터를 분석하고 변환하는 중입니다..."):
            
            # --- [Step 1] 원본 데이터 불러오기 ---
            try:
                df_raw = pd.read_csv(file_raw, skiprows=1)
            except:
                file_raw.seek(0)
                df_raw = pd.read_csv(file_raw)

            # TPND, TPNB 열 제거
            cols_to_drop = [c for c in ['TPND', 'TPNB'] if c in df_raw.columns]
            if cols_to_drop:
                df_raw = df_raw.drop(columns=cols_to_drop)

            # --- [Step 2] 상품코드 매핑 (바코드 -> ME코드) ---
            if '상품코드' in df_raw.columns:
                df_raw['상품코드'] = pd.to_numeric(df_raw['상품코드'], errors='coerce')
            df_prod['바코드'] = pd.to_numeric(df_prod['바코드'], errors='coerce')
            
            df_raw = pd.merge(df_raw, df_prod[['바코드', 'ME코드']], 
                              left_on='상품코드', right_on='바코드', how='left')

            # --- [Step 3] 발주/배송코드 조건부 할당 ---
            df_raw['발주코드'] = 81020000
            
            def get_delivery_code(store, in_type):
                store_str = str(store).strip()
                type_str = str(in_type).strip()
                
                if '안성' in store_str:
                    if 'FLOW' in type_str: return 81020981
                    if 'SORT' in type_str: return 81020980
                elif '함안' in store_str:
                    if 'FLOW' in type_str: return 81040912
                    return 81040913 
                return np.nan

            if '납품처' in df_raw.columns and '입고타입' in df_raw.columns:
                df_raw['배송코드'] = df_raw.apply(
                    lambda row: get_delivery_code(row['납품처'], row['입고타입']), axis=1
                )
                df_raw['배송코드'] = df_raw['배송코드'].fillna(81040913)

            # --- [Step 4] 컬럼명 변경 및 수량 필터링 ---
            df_result = df_raw.rename(columns={
                'ME코드': '상품코드',
                '낱개수량': '수량',
                '낱개당 단가': 'UNIT단가',
                '발주금액': 'Amount'
            })

            # 수량이 0이거나 빈 값 제거
            df_result['수량'] = pd.to_numeric(df_result['수량'], errors='coerce').fillna(0)
            df_result = df_result[df_result['수량'] > 0]

            final_cols = ['발주코드', '배송코드', '상품코드', '상품명', '수량', 'UNIT단가', 'Amount']
            exist_cols = [c for c in final_cols if c in df_result.columns]
            df_final = df_result[exist_cols].copy()
            
            if '배송코드' in df_final.columns:
                df_final['배송코드'] = df_final['배송코드'].astype(int)

            # --- [Step 5] 동일 품목 수량/금액 합산 (그룹핑) ---
            groupby_cols = ['발주코드', '배송코드', '상품코드', '상품명', 'UNIT단가']
            if all(col in df_final.columns for col in groupby_cols):
                df_final = df_final.groupby(groupby_cols, as_index=False).agg({
                    '수량': 'sum',
                    'Amount': 'sum'
                })
                # 배송코드 및 상품코드 순으로 정렬
                df_final = df_final.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            st.success("✅ 매핑 및 그룹핑 완료! 엑셀 파일이 준비되었습니다.")
            st.dataframe(df_final) # 화면에 결과 미리보기 출력

            # --- [Step 6] 엑셀(.xlsx) 파일 생성 및 다운로드 ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='수주데이터')
            
            st.download_button(
                label="📥 최종 수주 파일 다운로드 (Excel)",
                data=output.getvalue(),
                file_name="최종수주_정제완료.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        st.warning("원본 데이터 파일 형식이 맞는지 다시 한 번 확인해주세요.")
else:
    st.info("👈 메인 화면에 원본 데이터를 업로드해주세요.")
