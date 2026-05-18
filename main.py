import streamlit as st
from modules.english_agent import render_english_module
from modules.interview_agent import render_interview_module
from utils.logger import logger


def main():
    # 页面全局配置
    st.set_page_config(page_title="A-Scholar 智研导师", layout="wide", page_icon="🎓")

    if not check_password():
        st.stop()

    # 侧边栏
    with st.sidebar:
        st.title("🎓 A-Scholar")
        st.write("你的AI专属智研导师")
        st.divider()
        module_choice = st.radio(
            "导航菜单",
            ["🏠 首页", "🗣️ 凌云语境 (英语练习)", "👔 临渊实战 (仿真面试)"]
        )

    # 路由控制
    if module_choice == "🏠 首页":
        st.title("欢迎来到 A-Scholar")
        st.markdown("请在左侧选择你需要使用的功能模块。")
    elif module_choice == "🗣️ 凌云语境 (英语练习)":
        render_english_module()
    elif module_choice == "👔 临渊实战 (仿真面试)":
        render_interview_module()


def check_password():
    if "password_correct" not in st.session_state:
         st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("### 🔒 A-sholar - 私人内部测试版")
        # 密码输入框
        pwd = st.text_input("请输入访问密码：", type="password")
        if pwd:
            # 这里的密码可以去 st.secrets 里配置 APP_PASSWORD = "123"
            if pwd == st.secrets.get("APP_PASSWORD"):
                st.session_state["password_correct"] = True
                st.rerun() # 密码正确，刷新页面显示主内容
            else:
                st.error("密码错误！")
        return False
    return True


if __name__ == "__main__":
    main()
