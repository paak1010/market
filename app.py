import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import csv
from datetime import date

st.set_page_config(page_title="Tesco 납품 데이터 자동화", layout="wide")

st.title("📦 Tesco 발주 데이터 자동 변환기 (날짜 추가본)")
st.write("Tesco 주문서(CSV/Excel)를 업로드하면 수주일자와 납품일자를 자동으로 포함합니다.")

# ==========================================
# 1. 마스터 데이터
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
    8809020349425: 'ME00621A08', 8809020349685: 'ME00621AS1', 8809020349692: 'ME00621AL1',
    8809020349708: 'ME00621AR1', 8809020349715: 'ME00621AG1', 8809020349722: 'ME00621AF9',
    8809020349371: 'ME90621GK3', 8809020349418: 'ME90621GK2', 8809020349388: 'ME90621GL3',
    8809020349050: 'ME90621GLO', 8809020349067: 'ME90621GM4', 8809020349074: 'ME90621GE1',
    8809020349203: 'ME90621HCR', 8809020349098: 'ME90621HSL', 8809020349104: 'ME90621SM4',
    8809020349210: 'ME90621SCM', 8809020349166: 'ME90621GO8', 8809020349906: 'ME90621GLL',
    8809020349944: 'ME90621FGC', 8809020340200: 'ME00621H37', 8809020340217: 'ME00621H38',
    8809020340170: 'ME00621C15', 8809020340187: 'ME00621S24', 8809020340194: 'ME00621AS3',
    8809020340606: 'ME00621C22', 8809020340590: 'ME00621H44', 8809020340712: 'ME90621TC1',
    8809020341627: 'ME00621FMC', 8809020341634: 'ME00621FMR', 8809020341641: 'ME00621FBR',
    8809020341207: 'ME80421DR2', 8809020341061: 'ME81921SLL', 8809020341054: 'ME81921SVV',
    8809020341801: 'ME81921SL1', 8809020342501: 'ME90521LD9', 8809020342518: 'ME90521GT2',
    8809020342495: 'ME90521GS2', 8809020349036: 'ME00621CM5', 8809020346509: 'ME90621AFE',
    8809020349968: 'ME00621H41', 8809020342433: 'ME90621AC4', 8809020343478: 'ME00621ABN',
    8809020342525: 'ME80421DCH', 8809020343683: 'ME90521WC4', 8809020343690: 'ME90521WC5',
    8809020343706: 'ME90521WC6', 8809020344338: 'ME00621FHH', 8809020344321: 'ME90621MAM'
}

RAW_STORE_MAP = {
    '0903목천물류서비스센터SORTATION': 81020901, '0903목천물류서비스센터FLOW': 81020902,
    '0903목천물류서비스센터STOCK': 81020903, '0982안성ADC물류센터STOCK': 81020982,
    '0907밀양EXP센터FLOW': 81021903, '0967일죽물류서비스센터FLOW': 81021904,
    '0905기흥물류서비스센터FLOW': 81021907, '0961밀양물류센터FLOW': 81040912,
    '0961밀양물류센터STOCK': 81040913, '0906NEW함안상온물류센터FLOW': 81040912,
    '0906NEW함안상온물류센터SORTATION': 81040913, '0906NEW함안상온물류센터SORTER': 81040913,
    '0982안성ADC물류센터SORTATION': 81020980, '0982안성ADC물류센터FLOW': 81020981,
    '0970함안EXP물류센터SORTATION': 89029018, '0970함안EXP물류센터FLOW': 81040913,
    '0982안성ADC물류센터SINGLE': 81020981, '0906NEW함안상온물류센터SINGLE': 81040912,
    '0968365용인DSCDSD': 81040904, '0969남양주EXP물류센터FLOW': 81040905,
    '0968365용인DSCSTOCK': 81040904, '0969남양주EXP물류센터STOCK': 81040905,
    '0931덕평EXP물류센터FLOW': 81040906, '0934오산Exp물류센터FLOW': 81040907,
    '0935오산365물류센터STOCK': 81040908, '2001BH)영통점DSD': 81020192,
    '2002BH)강서점DSD': 81020191, '2003BH)인천송도점DSD': 81020190,
    '0934오산EXP물류센터SORTATION': 81040907, '0907밀양EXP센터SORTATION': 81021903,
    '0905기흥물류서비스센터SORTATION': 81021901, '0051강서점DSD': 81020191
}

NORMALIZED_STORE_MAP = {}
for k, v in RAW_STORE_MAP.items():
    norm_k = re.sub(r'^\d+', '', k).replace(" ", "").upper()
    NORMALIZED_STORE_MAP[norm_k] = v

# ==========================================
# 2. 메인 로직
# ==========================================
raw_file = st.file_uploader("발주 원본 파일을 올려주세요.", type=['xlsx', 'xls', 'csv'])

if raw_file:
    try:
        with st.spinner("날짜 데이터를 포함하여 변환 중입니다..."):
            all_rows = []
            if raw_file.name.endswith('.csv') or '.csv' in raw_file.name.lower():
                content = raw_file.getvalue()
                try: text = content.decode('utf-8-sig')
                except: text = content.decode('cp949')
                reader = csv.reader(io.StringIO(text))
                all_rows = [row for row in reader]
            else:
                try:
                    tables = pd.read_html(io.BytesIO(raw_file.getvalue()), encoding='utf-8')
                    for t in tables: all_rows.extend(t.fillna('').astype(str).values.tolist())
                except:
                    try:
                        tables = pd.read_html(io.BytesIO(raw_file.getvalue()), encoding='cp949')
                        for t in tables: all_rows.extend(t.fillna('').astype(str).values.tolist())
                    except:
                        df_temp = pd.read_excel(raw_file, header=None, engine='openpyxl')
                        all_rows = df_temp.fillna('').astype(str).values.tolist()

            parsed_data = []
            col_map = {}
            
            for row in all_rows:
                row_strs = [str(x).strip() for x in row]
                
                # 헤더 검색
                if '상품코드' in row_strs and ('발주금액' in row_strs or '낱개수량' in row_strs):
                    col_map = {
                        '상품명': row_strs.index('상품명') if '상품명' in row_strs else -1,
                        '상품코드': row_strs.index('상품코드'),
                        '입고타입': row_strs.index('입고타입') if '입고타입' in row_strs else -1,
                        '수량': row_strs.index('낱개수량') if '낱개수량' in row_strs else -1,
                        '단가': row_strs.index('낱개당 단가') if '낱개당 단가' in row_strs else -1,
                        '금액': row_strs.index('발주금액') if '발주금액' in row_strs else -1,
                        '납품처': row_strs.index('납품처') if '납품처' in row_strs else -1,
                        '납품일자': row_strs.index('납품일자') if '납품일자' in row_strs else -1
                    }
                    continue
                    
                if not col_map: continue
                
                try:
                    b_idx = col_map['상품코드']
                    if b_idx >= len(row_strs): continue
                    
                    b_str = re.sub(r'[^\d]', '', row_strs[b_idx])
                    if not b_str: continue
                    barcode = int(b_str)
                    
                    if barcode in FULL_PRODUCT_MAP:
                        def get_val(key):
                            idx = col_map[key]
                            if idx != -1 and idx < len(row_strs):
                                val = re.sub(r'[^\d.]', '', row_strs[idx])
                                return float(val) if val else 0.0
                            return 0.0
                            
                        def get_str(key):
                            idx = col_map[key]
                            return row_strs[idx] if idx != -1 and idx < len(row_strs) else ''

                        parsed_data.append({
                            '상품명': get_str('상품명'),
                            '바코드': barcode,
                            '입고타입': get_str('입고타입'),
                            '수량': get_val('수량'),
                            '단가': get_val('단가'),
                            '금액': get_val('금액'),
                            '납품처': get_str('납품처'),
                            '납품일자': get_str('납품일자')
                        })
                except Exception:
                    pass

            df = pd.DataFrame(parsed_data)
            
            # --- 매핑 로직 ---
            df['상품코드'] = df['바코드'].map(FULL_PRODUCT_MAP)
            
            def get_store_code(row):
                s = str(row['납품처']).replace(' ', '').upper()
                t = str(row['입고타입']).replace(' ', '').upper()
                if 'HYPER_FLOW' in t: t = 'FLOW'
                elif 'MIX' in t: t = 'SORTATION'
                s = re.sub(r'^\d+', '', s)
                key = s + t
                if key in NORMALIZED_STORE_MAP: return NORMALIZED_STORE_MAP[key]
                for norm_k, code in NORMALIZED_STORE_MAP.items():
                    if norm_k in key or key in norm_k: return code
                return 81040913
                
            df['배송코드'] = df.apply(get_store_code, axis=1)
            df['발주코드'] = 81020000
            
            # --- 합산 및 정렬 ---
            df = df[df['수량'] > 0]
            groupby_cols = ['발주코드', '배송코드', '상품코드', '상품명', '단가', '납품일자']
            df_grouped = df.groupby(groupby_cols, as_index=False).agg({'수량': 'sum', '금액': 'sum'})
            df_grouped = df_grouped.sort_values(by=['납품일자', '배송코드', '상품코드']).reset_index(drop=True)

            # --- 5. 최종 열 생성 및 날짜 형식 강제 지정 (YYYY-MM-DD) ---
            df_final = pd.DataFrame()
            
            # 수주일자: 오늘 날짜를 YYYY-MM-DD로
            df_final['수주일자'] = date.today().strftime('%Y-%m-%d')
            
            # 납품일자: pandas datetime 객체로 변환한 후 dt.strftime()을 이용해 완벽한 YYYY-MM-DD 문자로 변환
            df_final['납품일자'] = pd.to_datetime(df_grouped['납품일자'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            df_final['발주코드'] = df_grouped['발주코드'].astype(int)
            df_final['배송코드'] = df_grouped['배송코드'].astype(int)
            df_final['상품코드'] = df_grouped['상품코드']
            df_final['상품명'] = df_grouped['상품명']
            df_final['수량'] = df_grouped['수량'].astype(int)
            df_final['단가'] = df_grouped['단가'].astype(int)
            df_final['금액(Amount)'] = df_grouped['금액'].astype(int)

            # 최종 출력
            total_amount = df_final['금액(Amount)'].sum()
            st.success(f"✅ 처리가 완료되었습니다. (총액: {total_amount:,.0f}원)")
            st.dataframe(df_final, hide_index=True)

            # --- 6. 엑셀 다운로드 ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='수주결과')
                
            st.download_button(
                label="📥 날짜 포함 최종본 다운로드 (Excel)", 
                data=output.getvalue(), 
                file_name=f"Tesco_최종추출_{date.today().strftime('%m%d')}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"오류 발생: {e}")
