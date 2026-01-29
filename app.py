import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import time
import io

# --- Page Config ---
st.set_page_config(
    page_title="타 부서 요청 업무 트래킹",
    page_icon="⏱️",
    layout="centered"
)

# --- CSS for better UI ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- Supabase Setup ---
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error("Supabase 연결 정보를 확인해주세요. (st.secrets)")
    st.stop()

# --- Session State Initialization ---
if 'timer_start' not in st.session_state:
    st.session_state.timer_start = None
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'elapsed_time' not in st.session_state:
    st.session_state.elapsed_time = 0

# --- App Logic ---
st.title("⏱️ 타 부서 요청 업무 트래킹")
st.caption("팀원들이 타 부서 업무에 사용하는 시간을 기록하는 앱입니다.")

# 1. 기본 정보 입력
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("👤 팀원 이름", placeholder="이름을 입력하세요.")
    with col2:
        requested_dept = st.text_input("🏢 요청 부서", placeholder="요청한 부서명")

    task = st.text_area("📝 업무 내용", placeholder="수행한 업무의 상세 내용을 입력하세요.")

# 2. 시간 입력 방식 선택
st.divider()
input_mode = st.radio("⏳ 시간 입력 방식 선택", ["타이머 사용", "직접 입력"], horizontal=True)

duration_min = 0

if input_mode == "타이머 사용":
    st.subheader("⏱️ 타이머")
    
    # 타이머 표시용 컨테이너
    metric_placeholder = st.empty()
    
    col_t1, col_t2, col_t3 = st.columns(3)
    
    if st.session_state.is_running:
        elapsed = time.time() - st.session_state.timer_start
        metric_placeholder.metric("진행 시간", f"{int(elapsed // 60)}분 {int(elapsed % 60)}초")
        
        if col_t2.button("🛑 종료", type="primary"):
            final_elapsed = time.time() - st.session_state.timer_start
            st.session_state.elapsed_time = round(final_elapsed / 60, 2)
            st.session_state.is_running = False
            st.session_state.timer_start = None
            st.rerun()
        
        # 실시간 업데이트를 위해 주기적으로 리런 (Streamlit 특성상)
        time.sleep(1)
        st.rerun()
    else:
        if st.session_state.elapsed_time > 0:
            metric_placeholder.metric("최종 소요 시간", f"{st.session_state.elapsed_time} 분")
            duration_min = st.session_state.elapsed_time
        else:
            metric_placeholder.metric("진행 시간", "0분 0초")

        if col_t1.button("▶️ 시작", type="secondary"):
            st.session_state.timer_start = time.time()
            st.session_state.is_running = True
            st.session_state.elapsed_time = 0
            st.rerun()
            
        if col_t3.button("🔄 초기화"):
            st.session_state.elapsed_time = 0
            st.rerun()

else:
    duration_min = st.number_input("⏰ 소요 시간 (분 단위)", min_value=1, step=1, value=30)

# 3. 기록하기 버튼
st.divider()
if st.button("🚀 기록하기", type="primary", use_container_width=True):
    if not name or not requested_dept or not task:
        st.warning("모든 필드를 입력해주세요.")
    elif duration_min <= 0 and not st.session_state.is_running:
        st.warning("소요 시간이 0입니다. 타이머를 사용하거나 직접 입력해주세요.")
    else:
        try:
            data = {
                "name": name,
                "requested_dept": requested_dept,
                "task": task,
                "duration_min": duration_min
            }
            response = supabase.table("department_work_log").insert(data).execute()
            st.success("✅ 성공적으로 기록되었습니다!")
            # Reset
            st.session_state.elapsed_time = 0
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {e}")

# 4. 관리자 기능: 엑셀 다운로드
st.divider()
st.subheader("📊 데이터 관리 (관리자)")

if st.button("📥 전체 기록 엑셀 다운로드", use_container_width=True):
    try:
        res = supabase.table("department_work_log").select("*").order("created_at", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        if df.empty:
            st.info("기록된 데이터가 없습니다.")
        else:
            # 엑셀 파일 생성
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='WorkLog')
            
            processed_data = output.getvalue()
            
            st.download_button(
                label="📁 엑셀 파일 받기",
                data=processed_data,
                file_name=f"department_work_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
