import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기 (엑셀 업로드 전용)")
st.write("발주 시스템에서 다운받은 **원본 엑셀 파일(.xlsx)** 하나만 올리면 바로 최종 정제된 엑셀을 뽑아줍니다.")

# ==========================================
# 1. 내장형 마스터 데이터
# ==========================================
PRODUCT_MAP = {
    8809020346592: "ME90621ADI",  # 딥클렌저 100G
    8809020346509: "ME90621AFE",  # 포밍워시 200ML
    8809020345267: "ME80421DR2",  # 마사지롤온로션 50ML
    8809020345212: "ME00421186",  # 스프레이파이쿨 180ML
    8809020345229: "ME00421301"   # 스프레이익스트림 180ML
}

# ==========================================
# 2. 메인 화면: 원본 엑셀 파일 업로드
# ==========================================
file_raw = st.file_uploader("발주 시스템에서 다운받은 원본 엑셀 파일(.xlsx) 하나만 올려주세요.", type=['xlsx', 'xls'])

if file_raw:
    try:
        with st.spinner("엑셀 데이터를 읽고 정제하는 중입니다..."):
            
            # --- [Step 1] 원본 엑셀 데이터 불러오기 ---
            try:
                df_raw = pd.read_excel(file_raw, skiprows=1, engine='openpyxl')
            except:
                file_raw.seek(0)
                df_raw = pd.read_excel(file_raw, engine='openpyxl')

            # 불필요한 열 제거
            cols_to_drop = [c for c in ['TPND', 'TPNB'] if c in df_raw.columns]
            if cols_to_drop:
                df_raw = df_raw.drop(columns=cols_to_drop)

            # --- [Step 2] 상품코드 매핑 ---
            if '상품코드' in df_raw.columns:
                df_raw['바코드_숫자'] = pd.to_numeric(df_raw['상품코드'], errors='coerce')
                df_raw['ME코드'] = df_raw['바코드_숫자'].map(PRODUCT_MAP)
                
                # [★에러 해결 핵심★] 원래 있던 숫자 형태의 '상품코드' 열을 미리 삭제!
                # (그래야 나중에 'ME코드' 이름을 '상품코드'로 바꿀 때 충돌이 안 납니다)
                df_raw = df_raw.drop(columns=['상품코드'])
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
                df_raw['배송코드'] = df_raw['배송코드'].fillna(81040913)

            # --- [Step 4] 컬럼명 변경 및 수량 필터링 ---
            df_result = df_raw.rename(columns={
                'ME코드': '상품코드',   # 이제 중복 없이 깔끔하게 이름이 바뀝니다.
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
                # 정렬
                df_final = df_final.sort_values(by=['배송코드', '상품코드']).reset_index(drop=True)

            # 화면에 결과 출력
            st.success("✅ 엑셀 데이터 분석 및 그룹핑 완료! (중복 에러 해결됨)")
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
