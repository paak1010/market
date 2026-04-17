import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기")
st.write("""
원본 데이터(ordview_...)만 업로드하면, 서식파일 및 Summary 시트 규격에 맞춰 
**수량이 0이 아닌 유효 데이터만 추출**하여 다운로드할 수 있게 해줍니다.
""")

# 1. 사이드바: 마스터 데이터 업로드 (기준 정보)
st.sidebar.header("⚙️ 기초 마스터 데이터 설정")
st.sidebar.info("최초 1회만 업로드해두면 됩니다. (엑셀 파일에서 추출한 csv 파일)")
file_product = st.sidebar.file_uploader("1. 상품코드 마스터 (바코드-ME코드)", type=['csv'])
file_store = st.sidebar.file_uploader("2. 발주처코드 마스터", type=['csv'])

# 2. 메인 화면: 원본 데이터 업로드
st.header("📂 오늘의 원본 데이터 업로드")
file_raw = st.file_uploader("발주 시스템에서 다운받은 원본 데이터(csv)를 올려주세요.", type=['csv'])

if file_raw and file_product and file_store:
    try:
        with st.spinner("데이터를 분석하고 매핑하는 중입니다..."):
            # 데이터 불러오기 (원본은 첫 줄이 불필요한 메타데이터일 수 있어 1줄 건너뜀)
            try:
                df_raw = pd.read_csv(file_raw, skiprows=1)
            except:
                file_raw.seek(0)
                df_raw = pd.read_csv(file_raw)
                
            df_prod = pd.read_csv(file_product)
            df_store = pd.read_csv(file_store)

            # --- [Step 1] 원본 데이터 전처리 ---
            # TPND, TPNB 열 제거
            cols_to_drop = [c for c in ['TPND', 'TPNB'] if c in df_raw.columns]
            if cols_to_drop:
                df_raw = df_raw.drop(columns=cols_to_drop)
            
            # 상품코드 숫자 변환
            if '상품코드' in df_raw.columns:
                df_raw['상품코드'] = pd.to_numeric(df_raw['상품코드'], errors='coerce')

            # --- [Step 2] 상품코드 변환 (바코드 -> ME코드) ---
            # df_prod에 '바코드'와 'ME코드' 컬럼이 있다고 가정
            df_prod['바코드'] = pd.to_numeric(df_prod['바코드'], errors='coerce')
            df_raw = pd.merge(df_raw, df_prod[['바코드', 'ME코드']], 
                              left_on='상품코드', right_on='바코드', how='left')

            # --- [Step 3] 발주처/배송코드 매핑 ---
            # 납품처와 입고타입을 조합하여 '납품처&타입' 키 생성
            if '납품처' in df_raw.columns and '입고타입' in df_raw.columns:
                df_raw['매핑키'] = df_raw['납품처'].astype(str).str.strip() + df_raw['입고타입'].astype(str).str.strip()
                df_store['납품처&타입'] = df_store['납품처&타입'].astype(str).str.strip()
                
                df_raw = pd.merge(df_raw, df_store[['납품처&타입', '발주처코드', '배송코드']], 
                                  left_on='매핑키', right_on='납품처&타입', how='left')

            # --- [Step 4] 원하는 규격으로 컬럼명 변경 및 필터링 ---
            # 요구사항: 발주코드, 배송코드, 상품코드(ME), 상품명, 수량, UNIT단가, Amount
            df_result = df_raw.rename(columns={
                '발주처코드': '발주코드',
                'ME코드': '상품코드',      # 병합된 ME코드를 최종 상품코드로 사용
                '낱개수량': '수량',
                '낱개당 단가': 'UNIT단가',
                '발주금액': 'Amount'
            })

            # 수량이 0이거나 NaN인 값 제외
            df_result['수량'] = pd.to_numeric(df_result['수량'], errors='coerce').fillna(0)
            df_result = df_result[df_result['수량'] > 0]

            # 최종 출력할 컬럼만 선택
            final_cols = ['발주코드', '배송코드', '상품코드', '상품명', '수량', 'UNIT단가', 'Amount']
            # 실제로 존재하는 컬럼만 교집합으로 추출 (에러 방지)
            exist_cols = [c for c in final_cols if c in df_result.columns]
            df_final = df_result[exist_cols]

            st.success("✅ 변환이 완료되었습니다!")
            st.dataframe(df_final)

            # 다운로드 버튼 제공
            csv = df_final.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Summary 최종 데이터 다운로드 (CSV)",
                data=csv,
                file_name="Tesco_Summary_자동추출결과.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        st.warning("업로드하신 파일의 컬럼명(바코드, ME코드, 납품처 등)이 기존 양식과 일치하는지 확인해주세요.")
else:
    st.info("👈 사이드바에 마스터 데이터 2개와 메인 화면에 원본 데이터를 모두 업로드해주세요.")
