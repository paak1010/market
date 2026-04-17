import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Tesco 발주 데이터 자동 변환기", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기 (마스터파일 연동형)")
st.write("하드코딩 없이 **'Tesco 서식파일(마스터)'**의 시트 정보를 읽어와서 원본 데이터를 완벽하게 변환합니다.")

# ==========================================
# 1. 파일 업로드 섹션 (두 개 모두 올려주세요)
# ==========================================
col1, col2 = st.columns(2)
with col1:
    st.subheader("1️⃣ 마스터 서식파일 업로드")
    master_file = st.file_uploader("Tesco 서식파일(914)...xlsx 를 올려주세요.", type=['xlsx', 'xls'], key="master")

with col2:
    st.subheader("2️⃣ 원본 데이터 업로드")
    raw_file = st.file_uploader("발주 원본 파일 (예: 12.xlsx) 을 올려주세요.", type=['xlsx', 'xls', 'csv'], key="raw")

if master_file and raw_file:
    try:
        with st.spinner("마스터 서식파일의 규칙을 분석하고 데이터를 변환하는 중입니다..."):
            
            # ==========================================
            # [Step 1] 마스터 파일에서 기준 정보 읽기 (핵심!)
            # ==========================================
            # 1. 상품코드 매핑 데이터 가져오기
            df_prod_master = pd.read_excel(master_file, sheet_name='상품코드', engine='openpyxl')
            df_prod_master['바코드'] = pd.to_numeric(df_prod_master['바코드'], errors='coerce')
            valid_prods = df_prod_master.dropna(subset=['바코드', 'ME코드'])
            PRODUCT_MAP = dict(zip(valid_prods['바코드'], valid_prods['ME코드']))

            # 2. 발주처코드 매핑 데이터 가져오기 ('납품처&타입' 활용)
            df_store_master = pd.read_excel(master_file, sheet_name='Tesco 발주처코드', engine='openpyxl')
            valid_stores = df_store_master.dropna(subset=['납품처&타입', '배송코드']).copy()
            valid_stores['납품처&타입'] = valid_stores['납품처&타입'].astype(str).str.replace(" ", "") # 공백 제거하여 매핑 정확도 높임
            STORE_MAP = dict(zip(valid_stores['납품처&타입'], valid_stores['배송코드']))

            # ==========================================
            # [Step 2] 원본 데이터 읽기 및 정제
            # ==========================================
            # csv, xlsx 모두 지원하도록 처리
            if raw_file.name.endswith('.csv'):
                df_raw = pd.read_csv(raw_file, skiprows=1)
            else:
                df_raw = pd.read_excel(raw_file, skiprows=1, engine='openpyxl')

            # TPND, TPNB 열 제거
            cols_to_drop = [c for c in ['TPND', 'TPNB'] if c in df_raw.columns]
            if cols_to_drop:
                df_raw = df_raw.drop(columns=cols_to_drop)

            # ==========================================
            # [Step 3] 상품코드 변환 (서식파일 기준)
            # ==========================================
            if '상품코드' in df_raw.columns:
                df_raw['바코드_숫자'] = pd.to_numeric(df_raw['상품코드'], errors='coerce')
                # 서식파일에서 추출한 수백개의 매핑 딕셔너리로 한 번에 변환
                df_raw['ME코드'] = df_raw['바코드_숫자'].map(PRODUCT_MAP)
                df_raw = df_raw.drop(columns=['상품코드']) # 기존 바코드 열은 삭제
            else:
                df_raw['ME코드'] = None

            # ==========================================
            # [Step 4] 배송코드 변환 (서식파일 기준)
            # ==========================================
            df_raw['발주코드'] = 81020000

            def get_delivery_code(store, in_type):
                store_str = str(store)
                type_str = str(in_type)
                
                # 원본 데이터의 납품처와 입고타입을 붙임 (공백 무시)
                raw_key = (store_str + type_str).replace(" ", "")
                
                # 1. 서식파일 '납품처&타입'과 정확히 일치하는지 확인
                if raw_key in STORE_MAP:
                    return STORE_MAP[raw_key]
                
                # 2. HYPER_FLOW나 MIX 등 특수 케이스 보정 (서식파일에 FLOW/SORTATION으로 되어있을 경우)
                if 'HYPER_FLOW' in type_str:
                    fallback_key = (store_str + 'FLOW').replace(" ", "")
                    if fallback_key in STORE_MAP: return STORE_MAP[fallback_key]
                elif 'MIX' in type_str:
                    fallback_key = (store_str + 'SORTATION').replace(" ", "")
                    if fallback_key in STORE_MAP: return STORE_MAP[fallback_key]
                
                return None

            if '납품처' in df_raw.columns and '입고타입' in df_raw.columns:
                df_raw['배송코드'] = df_raw.apply(
                    lambda row: get_delivery_code(row['납품처'], row['입고타입']), axis=1
                )
                df_raw['배송코드'] = df_raw['배송코드'].fillna(81040913) # 기본값 처리

            # ==========================================
            # [Step 5] 최종 컬럼 정리 및 수량 합산
            # ==========================================
            df_result = df_raw.rename(columns={
                'ME코드': '상품코드',
                '낱개수량': '수량',
                '낱개당 단가': 'UNIT단가',
                '발주금액': 'Amount'
            })

            # 수량이 0인 항목 제거
            df_result['수량'] = pd.to_numeric(df_result['수량'], errors='coerce').fillna(0)
            df_result = df_result[df_result['수량'] > 0]

            final_cols = ['발주코드', '배송코드', '상품코드', '상품명', '수량', 'UNIT단가', 'Amount']
            exist_cols = [c for c in final_cols if c in df_result.columns]
            df_final = df_result[exist_cols].copy()
            
            if '배송코드' in df_final.columns:
                df_final['배송코드'] = df_final['배송코드'].astype(int)

            # 동일 상품 합산(그룹핑)
            groupby_cols = ['발주코드', '배송코드', '상품코드', '상품명', 'UNIT단가']
            if all(col in df_final.columns for col in groupby_cols):
                df_final = df_final.groupby(groupby_cols, as_index=False).agg({
                    '수량': 'sum',
                    'Amount': 'sum'
                })
                df_final = df_final.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            # ==========================================
            # [Step 6] 결과 출력 및 엑셀 다운로드
            # ==========================================
            st.success("✅ 마스터 파일의 규칙을 적용하여 완벽하게 변환되었습니다!")
            st.dataframe(df_final)

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
        st.error(f"오류 발생: {e}")
        st.warning("파일이 올바른 형식인지 다시 확인해주세요.")
else:
    st.info("👈 위 두 칸에 파일을 모두 업로드해주세요.")
