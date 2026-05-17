import streamlit as st
from utils.llm_client import get_llm_response


def render_interview_module():
    st.header("👔 临渊实战 - 仿真面试与答辩")

    # 状态机初始化
    if "interview_stage" not in st.session_state:
        st.session_state.interview_stage = "SETUP"

    if st.session_state.interview_stage == "SETUP":
        st.subheader("第一步：配置面试环境")
        col1, col2 = st.columns(2)
        scenario = col1.selectbox("面试场景", ["考研复试", "保研面试", "博士申请", "毕业答辩"])
        style = col2.selectbox("考官风格", ["温和引导", "严肃严谨", "极限高压(压力面)"])

        uploaded_file = st.file_uploader("上传简历或PPT (目前支持提取文本的PDF)", type=["pdf"])

        if st.button("🚀 开始面试"):
            # 这里应加入解析PDF的逻辑，并将提取的文本存入 st.session_state.context
            st.session_state.context = "假设这是提取出来的简历亮点..."
            st.session_state.interview_stage = "INTERVIEWING"
            st.session_state.interview_history = []
            st.rerun()

    elif st.session_state.interview_stage == "INTERVIEWING":
        st.subheader("🔴 面试进行中...")
        # 渲染对话... 逻辑类似于英语模块
        # ...
        if st.button("🛑 结束面试，生成报告"):
            st.session_state.interview_stage = "EVALUATION"
            st.rerun()

    elif st.session_state.interview_stage == "EVALUATION":
        st.subheader("📊 面试复盘报告")
        with st.spinner("AI正在根据刚才的面试表现生成详尽报告..."):
            # 调用LLM，将 st.session_state.interview_history 传给模型打分
            st.success("报告生成完毕！")
            st.write("专业知识评分: 85/100")
            st.write("改进建议: 在被问到XXX时，你的回答稍显犹豫，可以尝试采用STAR法则...")

        if st.button("重新开始"):
            st.session_state.interview_stage = "SETUP"
            st.rerun()