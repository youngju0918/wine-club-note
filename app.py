import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- 데이터베이스 초기화 함수 ---
def init_db():
    conn = sqlite3.connect('wine_club.db')
    c = conn.cursor()
    # 1. 와인 테이블 (grape 컬럼 추가)
    c.execute('''CREATE TABLE IF NOT EXISTS wines
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, vintage TEXT, country TEXT, region TEXT, type TEXT, grape TEXT,
                  image_path TEXT, reg_date TEXT)''')
    # 2. 시음 노트 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS tasting_notes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  wine_id INTEGER, member_name TEXT, 
                  score INTEGER, sweetness INTEGER, acidity INTEGER, tannin INTEGER, body INTEGER,
                  aromas TEXT, comment TEXT, write_date TEXT)''')
    conn.commit()
    conn.close()

# 앱 실행 시 DB 초기화
init_db()

# --- 데이터베이스 조작 유틸리티 ---
def run_query(query, params=()):
    conn = sqlite3.connect('wine_club.db')
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_query(query, params=()):
    conn = sqlite3.connect('wine_club.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

# --- 아로마 옵션 정의 ---
PRIMARY_OPTIONS = [
    "🍒 붉은 과실 (딸기, 체리, 라즈베리, 자두)", 
    "🫐 검은 과실 (블랙베리, 블랙커런트, 블루베리)", 
    "🍋 시트러스 (레몬, 라임, 자몽, 오렌지)", 
    "🍑 핵과류 (복숭아, 살구, 청포도)", 
    "🍍 열대과일 (파인애플, 망고, 패션후르츠)",
    "🌹 꽃 (장미, 제비꽃, 아카시아, 국화)", 
    "🌿 허브/식물 (민트, 유칼립투스, 피망, 컷글라스)", 
    "🌶️ 향신료 (후추, 감초, 계피, 정향)"
]
SECONDARY_OPTIONS = [
    "🪵 오크 숙성 (바닐라, 삼나무, 토스트, 코코넛)", 
    "🧈 유산 발효 (버터, 크림, 요거트, 치즈)", 
    "🍞 효모 숙성 (구운 빵, 비스킷, 브리오슈, 막걸리 향)"
]
TERTIARY_OPTIONS = [
    "🍂 자연/동물 (흙, 버섯, 가죽, 육류, 사냥고기, 낙엽)", 
    "🍇 숙성 과실 (말린 자두, 건포도, 무화과, 잼)", 
    "🍫 기타 숙성 (초콜릿, 커피, 담배, 견과류, 꿀, 타르)"
]

def combine_aromas(p_list, s_list, t_list):
    parts = []
    if p_list:
        parts.append(f"[1차] {', '.join([a.split(' (')[0] for a in p_list])}")
    if s_list:
        parts.append(f"[2차] {', '.join([a.split(' (')[0] for a in s_list])}")
    if t_list:
        parts.append(f"[3차] {', '.join([a.split(' (')[0] for a in t_list])}")
    return " | ".join(parts) if parts else "없음"

# --- Streamlit UI 구성 ---
st.set_page_config(page_title="와인 동호회 테이스팅 노트", layout="wide")
st.title("🍷 와인 동호회 테이스팅 노트")

# 사이드바 네비게이션
menu = st.sidebar.radio("메뉴 이동", ["시음 노트 작성", "내 시음 노트 수정", "와인 등록 (회장님 전용)", "와인별 모아보기", "개인별 모아보기"])

# --- 1. 와인 등록 ---
if menu == "와인 등록 (회장님 전용)":
    st.header("새로운 와인 등록")
    with st.form("wine_reg_form"):
        w_name = st.text_input("와인 이름")
        w_vintage = st.text_input("빈티지")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            w_country = st.text_input("생산국 (예: 프랑스, 이탈리아)")
        with col2:
            w_region = st.text_input("세부 지역 (예: 부르고뉴, 론)")
        with col3:
            w_type = st.selectbox("와인 종류", ["레드", "화이트", "스파클링", "디저트"])
            
        # 품종 입력칸 추가 (가이드 텍스트 포함)
        w_grape = st.text_input("포도 품종 (예: 피노 누아, 샤르도네, 시라, 사바냥 등)")
            
        w_image = st.file_uploader("와인 사진 업로드", type=['png', 'jpg', 'jpeg'])
        submitted = st.form_submit_button("등록하기")
        
        if submitted and w_name:
            image_path = ""
            if w_image is not None:
                if not os.path.exists("uploads"):
                    os.makedirs("uploads")
                image_path = f"uploads/{w_image.name}"
                with open(image_path, "wb") as f:
                    f.write(w_image.getbuffer())
            
            # INSERT 쿼리에 grape 추가
            execute_query('''INSERT INTO wines (name, vintage, country, region, type, grape, image_path, reg_date) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                          (w_name, w_vintage, w_country, w_region, w_type, w_grape, image_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            st.success(f"[{w_type}] 와인 '{w_name}' 등록이 완료되었습니다!")

# --- 2. 시음 노트 작성 ---
elif menu == "시음 노트 작성":
    st.header("📝 시음 노트 작성")
    
    wines_df = run_query("SELECT id, name, vintage FROM wines")
    if wines_df.empty:
        st.warning("등록된 와인이 없습니다. 회장님께 와인 등록을 요청하세요.")
    else:
        wine_dict = {f"{row['name']} ({row['vintage']})": row['id'] for _, row in wines_df.iterrows()}
        selected_wine_label = st.selectbox("어떤 와인을 드셨나요?", list(wine_dict.keys()))
        selected_wine_id = wine_dict[selected_wine_label]
        
        member_name = st.text_input("본인 이름(또는 닉네임)을 입력하세요")
        
        st.markdown("### 테이스팅 평가")
        w_score = st.slider("⭐ 와인 총점 (Score)", 50, 100, 85, help="50점부터 100점 만점 기준으로 평가해 주세요.")
        
        st.markdown("#### 맛 지표 체크리스트")
        col1, col2 = st.columns(2)
        with col1:
            sweetness = st.slider("당도 (Sweetness)", 1, 5, 3)
            acidity = st.slider("산도 (Acidity)", 1, 5, 3)
        with col2:
            tannin = st.slider("타닌 (Tannin)", 1, 5, 3)
            body = st.slider("바디감 (Body)", 1, 5, 3)
            
        st.markdown("#### 👃 아로마(향) 세부 체크리스트")
        selected_primary = st.multiselect("1차향 (포도 품종 자체와 발효에서 오는 과실·꽃·허브향)", PRIMARY_OPTIONS)
        selected_secondary = st.multiselect("2차향 (오크 숙성, 유산 발효, 효모 접촉 등 양조 과정의 향)", SECONDARY_OPTIONS)
        selected_tertiary = st.multiselect("3차향 (장기 병 숙성에서 오는 축적된 숙성향)", TERTIARY_OPTIONS)
        
        comment = st.text_area("자유로운 한줄평 (선택)")
        
        if st.button("노트 저장하기"):
            if member_name:
                aromas_str = combine_aromas(selected_primary, selected_secondary, selected_tertiary)
                execute_query('''INSERT INTO tasting_notes 
                                 (wine_id, member_name, score, sweetness, acidity, tannin, body, aromas, comment, write_date) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (selected_wine_id, member_name, w_score, sweetness, acidity, tannin, body, aromas_str, comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                st.success("시음 노트가 성공적으로 저장되었습니다!")
            else:
                st.error("이름을 입력해 주세요.")

# --- 3. 내 시음 노트 수정 ---
elif menu == "내 시음 노트 수정":
    st.header("✏️ 내가 작성한 노트 수정")
    m_name = st.text_input("노트를 수정할 본인의 이름(닉네임)을 입력하세요")
    
    if m_name:
        user_notes_df = run_query(f'''SELECT t.id as note_id, w.name, w.vintage 
                                      FROM tasting_notes t 
                                      JOIN wines w ON t.wine_id = w.id 
                                      WHERE t.member_name = ?''', (m_name,))
        
        if user_notes_df.empty:
            st.info(f"'{m_name}' 이름으로 작성된 시음 노트를 찾을 수 없습니다.")
        else:
            note_dict = {f"{row['name']} ({row['vintage']}) [ID: {row['note_id']}]": row['note_id'] for _, row in user_notes_df.iterrows()}
            selected_note_label = st.selectbox("수정할 노트를 선택하세요", list(note_dict.keys()))
            selected_note_id = note_dict[selected_note_label]
            
            orig = run_query("SELECT * FROM tasting_notes WHERE id = ?", (selected_note_id,)).iloc[0]
            
            st.markdown("---")
            st.subheader("기존 데이터 수정")
            new_score = st.slider("⭐ 와인 총점 수정", 50, 100, int(orig['score']))
            
            col1, col2 = st.columns(2)
            with col1:
                new_sweetness = st.slider("당도 수정", 1, 5, int(orig['sweetness']))
                new_acidity = st.slider("산도 수정", 1, 5, int(orig['acidity']))
            with col2:
                new_tannin = st.slider("타닌 수정", 1, 5, int(orig['tannin']))
                new_body = st.slider("바디감 수정", 1, 5, int(orig['body']))
                
            orig_aromas_str = orig['aromas'] if orig['aromas'] else ""
            default_p = [opt for opt in PRIMARY_OPTIONS if opt.split(' (')[0] in orig_aromas_str]
            default_s = [opt for opt in SECONDARY_OPTIONS if opt.split(' (')[0] in orig_aromas_str]
            default_t = [opt for opt in TERTIARY_OPTIONS if opt.split(' (')[0] in orig_aromas_str]
            
            new_primary = st.multiselect("1차향 수정", PRIMARY_OPTIONS, default=default_p)
            new_secondary = st.multiselect("2차향 수정", SECONDARY_OPTIONS, default=default_s)
            new_tertiary = st.multiselect("3차향 수정", TERTIARY_OPTIONS, default=default_t)
            
            new_comment = st.text_area("한줄평 수정", value=orig['comment'])
            
            if st.button("수정 완료하기"):
                new_aromas_str = combine_aromas(new_primary, new_secondary, new_tertiary)
                execute_query('''UPDATE tasting_notes 
                                 SET score=?, sweetness=?, acidity=?, tannin=?, body=?, aromas=?, comment=?, write_date=?
                                 WHERE id=?''', 
                              (new_score, new_sweetness, new_acidity, new_tannin, new_body, new_aromas_str, new_comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_note_id))
                st.success("시음 노트가 성공적으로 수정되었습니다!")
                st.rerun()

# --- 4. 와인별 모아보기 ---
elif menu == "와인별 모아보기":
    st.header("🍷 와인별 시음기")
    # grape 컬럼 추가 조회
    wines_df = run_query("SELECT id, name, vintage, country, region, type, grape FROM wines")
    
    if not wines_df.empty:
        wine_dict = {f"{row['name']} ({row['vintage']})": row['id'] for _, row in wines_df.iterrows()}
        selected_wine_label = st.selectbox("와인을 선택하세요", list(wine_dict.keys()))
        selected_wine_id = wine_dict[selected_wine_label]
        
        w_info = wines_df[wines_df['id'] == selected_wine_id].iloc[0]
        # 상단 안내 텍스트에 품종(grape) 정보 추가 반영
        st.markdown(f"**🌍 와인 정보:** {w_info['type']} 와인 | {w_info['country']} / {w_info['region']} | 🍇 품종: {w_info['grape']}")
        
        query = f"SELECT member_name as 작성자, score as 총점, sweetness as 당도, acidity as 산도, tannin as 타닌, body as 바디, aromas as 향, comment as 코멘트, write_date as 작성일 FROM tasting_notes WHERE wine_id = {selected_wine_id}"
        notes_df = run_query(query)
        
        if not notes_df.empty:
            stats_df = notes_df[['총점', '당도', '산도', '타닌', '바디']].dropna().mean().round(1)
            
            st.markdown("#### 회원들이 평가한 평균 지표")
            col0, col1, col2, col3, col4 = st.columns(5)
            col0.metric("🏅 평균 총점", f"{stats_df['총점']} 점")
            col1.metric("평균 당도", stats_df['당도'])
            col2.metric("평균 산도", stats_df['산도'])
            col3.metric("평균 타닌", stats_df['타닌'])
            col4.metric("평균 바디", stats_df['바디'])
            
            st.markdown("#### 상세 시음 노트")
            st.dataframe(notes_df, use_container_width=True)
        else:
            st.info("아직 이 와인에 대한 시음 노트가 없습니다.")

# --- 5. 개인별 모아보기 ---
elif menu == "개인별 모아보기":
    st.header("👤 개인별 시음 기록")
    
    users_df = run_query("SELECT DISTINCT member_name FROM tasting_notes")
    
    if not users_df.empty:
        selected_user = st.selectbox("회원을 선택하세요", users_df['member_name'].tolist())
        
        # 조인문 쿼리에 w.grape 추가
        query = f'''SELECT w.name as 와인명, w.vintage as 빈티지, w.type as 종류, w.country as 국가, w.region as 지역, w.grape as 품종,
                           t.score as 총점, t.sweetness as 당도, t.acidity as 산도, 
                           t.tannin as 타닌, t.body as 바디, t.aromas as 향, t.comment as 코멘트, t.write_date as 작성일 
                    FROM tasting_notes t 
                    JOIN wines w ON t.wine_id = w.id 
                    WHERE t.member_name = "{selected_user}"
                    ORDER BY t.write_date DESC'''
        user_notes_df = run_query(query)
        
        st.markdown(f"#### {selected_user}님이 마신 와인들")
        st.dataframe(user_notes_df, use_container_width=True)
    else:
        st.info("아직 작성된 시음 노트가 없습니다.")