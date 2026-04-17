import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기 (단독 실행 버전)")
st.write("다른 마스터 파일 업로드 필요 없이, **원본 데이터(ordview) 하나만 올리면** 바로 최종 엑셀을 뽑아줍니다.")

# ==========================================
# 1. 내장형 마스터 데이터 (코드 내부에 직접 정의)
# ==========================================
# 엑셀 파일 없이도 바코드를 ME코드로 자동 변환하도록 딕셔너리 내장
PRODUCT_MAP = {
    8809020346592: "ME90621ADI",  # 딥클렌저 100G
    8809020346509: "ME90621AFE",  # 포밍워시 200ML
    8809020345267: "ME80421DR2",  # 마사지롤온로션 50ML
    8809020345212: "ME00421186",  # 스프레이파이쿨 180ML
    8809020345229: "ME00421301"   # 스프레이익스트림 180ML
}
# (※ 나중에 새로운 상품이 추가되면 위 딕셔너리에 숫자와 ME코드만 한 줄 추가하시면 됩니다.)

# ==========================================
# 2. 메인 화면: 단일 원본 파일 업로드
# ==========================================
file_raw = st.file_uploader("발주 시스템에서 다운받은 원본 데이터(csv) 파일 하나만 올려주세요.", type=['csv'])

if file_raw:
    try:
        with st.spinner("데이터를 정제하고 그룹핑하는 중입니다..."):
            
            # --- [Step 1] 원본 데이터 불러오기 ---
            try:
                df_raw = pd.read_csv(file_raw, skiprows=1)
            except:
                file_raw.seek(0)
                df_raw = pd.read_csv(file_raw)

            # 불필요한 열 (TPND, TPNB) 제거
            cols_to_drop = [c for c in ['TPND', 'TPNB'] if c in df_raw.columns]
            if cols_to_drop:
                df_raw = df_raw.drop(columns=cols_to_drop)

            # --- [Step 2] 상품코드 매핑 (내장 데이터 활용) ---
            if '상품코드' in df_raw.columns:
                # 바코드를 숫자로 변환 후 내장된 PRODUCT_MAP을 통해 ME코드로 변경
                df_raw['바코드_숫자'] = pd.to_numeric(df_raw['상품코드'], errors='coerce')
                # 매핑된 ME코드가 있으면 그걸 쓰고, 없으면 원래 바코드 값 유지
                df_raw['ME코드'] = df_raw['바코드_숫자'].map(PRODUCT_MAP)
            else:
                df_raw['ME코드'] = np.nan

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
                df_raw['배송코드'] = df_raw['배송코드'].fillna(81040913) # 못 찾으면 함안 디폴트 할당

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
                # 배송코드 및 상품코드 순으로 깔끔하게 정렬
                df_final = df_final.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            # 화면에 결과 출력
            st.success("✅ 매핑 및 그룹핑 완료! (외부 파일 연동 없이 독립 실행 성공)")
            st.dataframe(df_final)

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
        st.error(f"데이터 처리 중 문제가 발생했습니다: {e}")
