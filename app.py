import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import csv
from datetime import date  # 날짜 계산을 위해 추가

# ... (기존 FULL_PRODUCT_MAP, RAW_STORE_MAP 등은 동일) ...

# --- 2. 진짜 데이터만 쏙쏙 뽑아내는 로직 (수정본) ---
parsed_data = []
col_map = {}

for row in all_rows:
    row_strs = [str(x).strip() for x in row]
    
    # '납품일자'를 찾기 위해 헤더 맵핑에 추가
    if '상품코드' in row_strs and ('발주금액' in row_strs or '낱개수량' in row_strs):
        col_map = {
            '상품명': row_strs.index('상품명') if '상품명' in row_strs else -1,
            '상품코드': row_strs.index('상품코드'),
            '입고타입': row_strs.index('입고타입') if '입고타입' in row_strs else -1,
            '수량': row_strs.index('낱개수량') if '낱개수량' in row_strs else -1,
            '단가': row_strs.index('낱개당 단가') if '낱개당 단가' in row_strs else -1,
            '금액': row_strs.index('발주금액') if '발주금액' in row_strs else -1,
            '납품처': row_strs.index('납품처') if '납품처' in row_strs else -1,
            '납품일자': row_strs.index('납품일자') if '납품일자' in row_strs else -1  # 추가
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
                '납품일자': get_str('납품일자') # 데이터 추출 추가
            })
    except Exception:
        pass

if parsed_data:
    df = pd.DataFrame(parsed_data)
    df['상품코드'] = df['바코드'].map(FULL_PRODUCT_MAP)
    
    # ... (get_store_code 함수 및 배송코드/발주코드 적용 동일) ...
    df['배송코드'] = df.apply(get_store_code, axis=1)
    df['발주코드'] = 81020000
    
    # --- 4. 합산 및 정렬 (납품일자 포함) ---
    df = df[df['수량'] > 0]
    # groupby 항목에 '납품일자' 추가 (같은 날짜끼리 묶기 위함)
    groupby_cols = ['발주코드', '배송코드', '상품코드', '상품명', '단가', '납품일자']
    df_grouped = df.groupby(groupby_cols, as_index=False).agg({'수량': 'sum', '금액': 'sum'})
    df_grouped = df_grouped.sort_values(by=['납품일자', '배송코드', '상품코드']).reset_index(drop=True)

    # --- 5. 최종 열 생성 (수주일자, 납품일자 추가) ---
    df_final = pd.DataFrame()
    df_final['수주일자'] = date.today().strftime('%Y-%m-%d') # 오늘 날짜 (YYYY-MM-DD)
    df_final['납품일자'] = df_grouped['납품일자']            # 원본에서 가져온 날짜
    df_final['발주코드'] = df_grouped['발주코드'].astype(int)
    df_final['배송코드'] = df_grouped['배송코드'].astype(int)
    df_final['상품코드'] = df_grouped['상품코드']
    df_final['상품명'] = df_grouped['상품명']
    df_final['수량'] = df_grouped['수량'].astype(int)
    df_final['단가'] = df_grouped['단가'].astype(int)
    df_final['금액(Amount)'] = df_grouped['금액'].astype(int)

    # ... (이하 동일: 합계 표시 및 다운로드 버튼) ...
