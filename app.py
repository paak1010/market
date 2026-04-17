import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기 (시트 이름 자동 인식)")
st.write("마스터 파일과 원본 파일 두 가지만 올려주시면 시트 이름을 알아서 찾아 변환해 드립니다.")

# ==========================================
# 1. 파일 업로드 섹션
# ==========================================
col1, col2 = st.columns(2)
with col1:
    st.subheader("1️⃣ 마스터 서식파일 업로드")
    master_file = st.file_uploader("Tesco 서식파일(914)...xlsx 를 올려주세요.", type=['xlsx', 'xls'])

with col2:
    st.subheader("2️⃣ 원본 데이터 업로드")
    raw_file = st.file_uploader("발주 원본 파일 (예: 12.xlsx) 을 올려주세요.", type=['xlsx', 'xls', 'csv'])

if master_file and raw_file:
    try:
        with st.spinner("마스터 파일 분석 중..."):
            # 엑셀 파일의 모든 시트 이름을 먼저 가져옵니다.
            xl_master = pd.ExcelFile(master_file)
            sheet_names = xl_master.sheet_names
            
            # [기능 추가] 시트 이름을 똑똑하게 찾기 (공백 무시, 단어 포함 여부 확인)
            prod_sheet = next((s for s in sheet_names if '상품' in s and '코드' in s), None)
            store_sheet = next((s for s in sheet_names if '발주' in s and '코드' in s), None)

            if not prod_sheet:
                st.error("❌ '상품코드' 시트를 찾을 수 없습니다. 시트 이름을 확인해주세요.")
                st.stop()
            if not store_sheet:
                st.error("❌ 'Tesco 발주처코드' 시트를 찾을 수 없습니다. 시트 이름을 확인해주세요.")
                st.stop()

            # 마스터 데이터 로드
            df_prod_master = pd.read_excel(master_file, sheet_name=prod_sheet, engine='openpyxl')
            df_store_master = pd.read_excel(master_file, sheet_name=store_sheet, engine='openpyxl')

            # 상품 매핑 사전 생성
            df_prod_master['바코드'] = pd.to_numeric(df_prod_master['바코드'], errors='coerce')
            valid_prods = df_prod_master.dropna(subset=['바코드', 'ME코드'])
            PRODUCT_MAP = dict(zip(valid_prods['바코드'], valid_prods['ME코드']))

            # 발주처 매핑 사전 생성
            valid_stores = df_store_master.dropna(subset=['납품처&타입', '배송코드']).copy()
            valid_stores['납품처&타입'] = valid_stores['납품처&타입'].astype(str).str.replace(" ", "")
            STORE_MAP = dict(zip(valid_stores['납품처&타입'], valid_stores['배송코드']))

        with st.spinner("데이터 변환 및 그룹핑 중..."):
            # 원본 데이터 로드
            if raw_file.name.endswith('.csv'):
                df_raw = pd.read_csv(raw_file, skiprows=1)
            else:
                df_raw = pd.read_excel(raw_file, skiprows=1, engine='openpyxl')

            # TPND, TPNB 삭제
            df_raw = df_raw.drop(columns=[c for c in ['TPND', 'TPNB'] if c in df_raw.columns])

            # 상품코드 매핑 및 중복 컬럼 처리
            if '상품코드' in df_raw.columns:
                df_raw['바코드_숫자'] = pd.to_numeric(df_raw['상품코드'], errors='coerce')
                df_raw['ME코드'] = df_raw['바코드_숫자'].map(PRODUCT_MAP)
                df_raw = df_raw.drop(columns=['상품코드']) # 기존 상품코드 열 삭제

            # 배송코드 매핑
            df_raw['발주코드'] = 81020000
            def get_delivery_code(store, in_type):
                store_str, type_str = str(store).strip(), str(in_type).strip()
                raw_key = (store_str + type_str).replace(" ", "")
                if raw_key in STORE_MAP: return STORE_MAP[raw_key]
                # HYPER_FLOW 보정 로직
                if 'HYPER_FLOW' in type_str:
                    fallback = (store_str + 'FLOW').replace(" ", "")
                    return STORE_MAP.get(fallback, 81040913)
                return STORE_MAP.get(raw_key, 81040913)

            df_raw['배송코드'] = df_raw.apply(lambda r: get_delivery_code(r['납품처'], r['입고타입']), axis=1)

            # 수량 합산 처리
            df_result = df_raw.rename(columns={'ME코드': '상품코드', '낱개수량': '수량', '낱개당 단가': 'UNIT단가', '발주금액': 'Amount'})
            df_result['수량'] = pd.to_numeric(df_result['수량'], errors='coerce').fillna(0)
            df_result = df_result[df_result['수량'] > 0]

            final_cols = ['발주코드', '배송코드', '상품코드', '상품명', '수량', 'UNIT단가', 'Amount']
            df_final = df_result[[c for c in final_cols if c in df_result.columns]].copy()
            df_final['배송코드'] = df_final['배송코드'].fillna(0).astype(int)

            # 동일 품목/가격 그룹핑 (합산)
            groupby_cols = ['발주코드', '배송코드', '상품코드', '상품명', 'UNIT단가']
            df_final = df_final.groupby(groupby_cols, as_index=False).agg({'수량': 'sum', 'Amount': 'sum'})
            df_final = df_final.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            st.success("✅ 변환 완료!")
            st.dataframe(df_final)

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='수주데이터')
            st.download_button("📥 최종 엑셀 다운로드", data=output.getvalue(), file_name="최종수주결과.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
