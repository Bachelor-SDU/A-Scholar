# modules/english_agent.py
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from audio_recorder_streamlit import audio_recorder

from utils.nlp_agents import EnglishAgents, UserDataStore
from utils.audio_client import transcribe_audio, generate_audio_reply
from utils.dict_api import lookup_word_youdao
from utils.logger import logger


class EnglishLinguaApp:
    def __init__(self):
        self.init_state()

    def init_state(self):
        if "lingua_history" not in st.session_state:
            greeting_en = "Hey there! How's your day going?"
            greeting_zh = "嗨！今天过得怎么样？"
            audio_bytes = generate_audio_reply(greeting_en)

            st.session_state.lingua_history = [{
                "role": "assistant",
                "content_en": greeting_en,
                "content_zh": greeting_zh,
                "audio": audio_bytes,
                "played": False
            }]
            st.session_state.hints = []
            st.session_state.diagnostics = {}

    def render_dictionary_tool(self):
        """全局查词器组件 (使用 popover 实现弹出词典)"""
        with st.popover("🔍 词典/查词"):
            word = st.text_input("输入单词或词组：")
            if word:
                with st.spinner("查询中..."):
                    res = EnglishAgents.dictionary_agent(word)
                    if res:
                        st.markdown(f"### {res['word']}  `{res['level']}`")
                        st.write(f"🇬🇧 /{res['uk_phonetic']}/ | 🇺🇸 /{res['us_phonetic']}/")
                        # 假设有个通用的发音按钮组件
                        # st.audio(generate_audio_reply(res['word']))
                        for m in res['meanings']:
                            st.write(f"**{m['pos']}** {m['def']}")

    # def render_dictionary_tool(self):
    #     """查词小工具 (极简弹窗 UI)"""
    #     # st.popover 是一个按钮，点击后会弹出一个浮动窗口
    #     with st.popover("🔍 划词/查词", use_container_width=True):
    #         st.markdown("**在线词典**")
    #
    #         # 使用一个表单，防止每敲一个字母就触发查询
    #         with st.form("dict_search_form", clear_on_submit=False):
    #             col_input, col_btn = st.columns([3, 1])
    #             with col_input:
    #                 word_query = st.text_input("输入英文单词或词组", label_visibility="collapsed")
    #             with col_btn:
    #                 submitted = st.form_submit_button("查询")
    #
    #         if submitted and word_query:
    #             with st.spinner("查询中..."):
    #                 dict_data = lookup_word_youdao(word_query)
    #
    #             if dict_data:
    #                 # ==========================================
    #                 # UI 渲染：单词头 与 考试标签
    #                 # ==========================================
    #                 st.markdown(f"### {dict_data['word']}")
    #
    #                 if dict_data['exam_type']:
    #                     # 将标签用 HTML 渲染成漂亮的小 Tag
    #                     tags_html = " ".join([
    #                                              f"<span style='background:#f0f2f6; padding:2px 8px; border-radius:10px; font-size:12px; color:#31333F;'>{tag}</span>"
    #                                              for tag in dict_data['exam_type']])
    #                     st.markdown(tags_html, unsafe_allow_html=True)
    #
    #                 st.divider()
    #
    #                 # ==========================================
    #                 # UI 渲染：音标与发音按钮 (使用 Streamlit 原生音频播放)
    #                 # ==========================================
    #                 col_uk, col_us = st.columns(2)
    #                 with col_uk:
    #                     if dict_data['uk_phonetic']:
    #                         st.caption(f"🇬🇧 英 `/{dict_data['uk_phonetic']}/`")
    #                         if dict_data['uk_speech']:
    #                             st.audio(dict_data['uk_speech'], format="audio/mp3")
    #
    #                 with col_us:
    #                     if dict_data['us_phonetic']:
    #                         st.caption(f"🇺🇸 美 `/{dict_data['us_phonetic']}/`")
    #                         if dict_data['us_speech']:
    #                             st.audio(dict_data['us_speech'], format="audio/mp3")
    #
    #                 st.write("")  # 换行留白
    #
    #                 # ==========================================
    #                 # UI 渲染：核心释义
    #                 # ==========================================
    #                 if dict_data['explains']:
    #                     for explain in dict_data['explains']:
    #                         st.markdown(f"- {explain}")
    #                 else:
    #                     st.markdown(f"**翻译:** {', '.join(dict_data['translation'])}")
    #
    #                 st.divider()
    #
    #                 # ==========================================
    #                 # 动作：收藏到生词本
    #                 # ==========================================
    #                 if st.button("⭐ 收藏到生词本", key=f"save_vocab_{dict_data['word']}", use_container_width=True):
    #                     # 调用我们前面规划的数据库保存接口
    #                     self.db.save_favorite(
    #                         content=dict_data['word'],
    #                         translation=dict_data['translation'][0],
    #                         type="word"
    #                     )
    #                     st.success(f"已加入词汇库！")
    #             else:
    #                 st.error("未找到该词汇，请检查拼写或网络。")

    def render_chat_tab(self):
        """核心板块一：对话UI渲染"""

        # 1. 顶部工具栏 (查词器)
        col1, col2 = st.columns([4, 1])
        with col2:
            self.render_dictionary_tool()

        # 2. 渲染历史消息
        for i, msg in enumerate(st.session_state.lingua_history):
            if msg["role"] == "assistant":
                self._render_ai_message(i, msg)
            else:
                self._render_user_message(i, msg)

        # 3. 提示词生成器 (Hint Button)
        if st.session_state.lingua_history[-1]["role"] == "assistant":
            col_h1, col_h2 = st.columns([1, 4])
            with col_h1:
                if st.button("💡 需要提示?"):
                    with st.spinner("生成提示中..."):
                        context = [{"role": m["role"], "content": m["content"]} for m in
                                   st.session_state.lingua_history[-3:]]
                        hints_data = EnglishAgents.hint_agent(context)
                        if hints_data:
                            st.session_state.hints = hints_data.get("hints", [])
                            st.rerun()
            with col_h2:
                if st.session_state.hints:
                    st.write("可以尝试这样回复：")
                    for h in st.session_state.hints:
                        st.caption(f"👉 {h}")

        # 4. 底部双模态输入区
        self._render_input_area()
        self._process_agent_pipeline()

    def _render_ai_message(self, index, msg):
        """渲染AI的消息气泡"""
        with st.chat_message("🎓"):
            st.markdown(f"**{msg['content_en']}**")

            if msg.get("content_zh"):
                with st.popover("🌐 翻译"):
                    st.write(msg["content_zh"])

            if msg.get("audio"):
                should_autoplay = not msg.get("played", True)
                st.audio(msg["audio"], format="audio/mp3", autoplay=should_autoplay)
                st.session_state.lingua_history[index]["played"] = True

    def _render_user_message(self, index, msg):
        """渲染用户消息气泡 & 诊断面板"""
        with st.chat_message("👤"):
            st.write(msg["content_en"])

            if index in st.session_state.diagnostics:
                diag = st.session_state.diagnostics[index]
                btn_label = "✅ 表达自然" if not diag.get("has_error") else "❗ 语法建议"
                btn_type = "primary" if diag.get("has_error") else "secondary"

                with st.expander(btn_label):
                    # --- Tab 1: 发音与原句 ---
                    st.markdown("### 🗣️ 原句与发音")
                    st.info(f"**您的表达:** {msg['content_en']}\n\n**翻译:** {diag.get('translation', '无')}")
                    st.caption(f"**Native 评价:** {diag.get('native_eval', '无')}")

                    if msg.get("audio"):
                        st.write("您的录音:")
                        st.audio(msg["audio"])

                    # --- Tab 2: 语法纠正 (视觉Diff) ---
                    if diag.get("has_error") and diag.get('correction'):
                        st.markdown("### 🛠️ 语法纠正")
                        old = diag['correction'].get('old_text', '')
                        new = diag['correction'].get('new_text', '')
                        if old and new:
                            diff_text = msg['content_en'].replace(old,
                                                                  f"<strike style='color:#e74c3c'>{old}</strike> <span style='color:#2ecc71; font-weight:bold'>{new}</span>")
                            st.markdown(diff_text, unsafe_allow_html=True)

                        st.success(
                            f"**完整修正:** {diag['correction'].get('full_sentence', '')}\n\n**翻译:** {diag['correction'].get('translation', '')}")

                    # --- Tab 3: 优化表达 (多场景) ---
                    st.markdown("### ✨ 升级表达")
                    tab_g, tab_i, tab_a = st.tabs(["通俗通用", "地道口语", "学术正式"])

                    def _render_alt(alt_data, tab_key):
                        if not alt_data: return
                        st.markdown(f"**{alt_data.get('text', '')}**")
                        st.write(f"翻译: {alt_data.get('trans', '')}")
                        st.caption(f"💡 分析: {alt_data.get('analysis', '')}")

                    alts = diag.get("alternatives", {})
                    with tab_g:
                        _render_alt(alts.get("general"), "g")
                    with tab_i:
                        _render_alt(alts.get("idiomatic"), "i")
                    with tab_a:
                        _render_alt(alts.get("academic"), "a")

    def _render_input_area(self):
        """输入处理逻辑"""

        # 初始化一个 state 用于记录上一次处理的音频长度，防止重复触发
        if "last_audio_len" not in st.session_state:
            st.session_state.last_audio_len = 0

        col_text, col_mic = st.columns([5, 1])
        with col_text:
            text_input = st.chat_input("Type here or use mic...")
        with col_mic:
            audio_bytes = audio_recorder(
                text="",
                icon_name="microphone",
                key="main_mic"
            )

        user_text = None
        user_audio = None

        if text_input:
            user_text = text_input

        elif audio_bytes and len(audio_bytes) != st.session_state.last_audio_len:
            st.session_state.last_audio_len = len(audio_bytes)  # 更新记录

            with st.spinner("Recognizing... (识别中)"):
                user_text = transcribe_audio(audio_bytes)
                user_audio = audio_bytes

                if not user_text:
                    st.warning("⚠️ 未能识别到声音，请大点声或检查麦克风权限。")
                    user_text = None  # 确保为 None，不往下走

        if user_text:
            st.session_state.lingua_history.append({
                "role": "user",
                "content_en": user_text,
                "audio": user_audio
            })

            st.session_state.pending_user_text = user_text
            if "tts_future" not in st.session_state:
                st.session_state.tts_future = None
            if "diag_future" not in st.session_state:
                st.session_state.diag_future = None
            st.session_state.agent_stage = "waiting_llm"

            st.rerun()

    def _process_agent_pipeline(self):
        stage = st.session_state.get("agent_stage")
        if not stage:
            return

        if stage == "waiting_llm":
            # 采用合并状态：一次性处理所有后台任务，体验更紧凑流畅
            with st.spinner("Thinking..."):
                user_text = st.session_state.pending_user_text

                # 1. 准备历史对话数据 (包含用户刚刚发送的消息)
                history_for_chat = [
                    {"role": m["role"], "content": m["content_en"]}
                    for m in st.session_state.lingua_history
                ]

                # 确定当前用户消息在历史记录中的索引（用于绑定诊断结果）
                user_index = len(st.session_state.lingua_history) - 1

                # =========================
                # 🚀 核心优化：高并发执行流水线
                # =========================
                with ThreadPoolExecutor(max_workers=3) as executor:

                    # 💥 优化点1：立即派发【诊断任务】（它只依赖用户文本，不需要等AI回答）
                    future_diag = executor.submit(
                        self._run_diag_task,
                        user_text,
                        history_for_chat
                    )

                    # 💥 优化点2：立即派发【对话任务】
                    future_chat = executor.submit(
                        EnglishAgents.chat_agent,
                        history_for_chat
                    )

                    # ⏳ 阻塞：等待【对话任务】完成（最耗时的部分，约2秒）
                    reply_data = future_chat.result()

                    if reply_data and "reply_en" in reply_data:
                        reply_en = reply_data["reply_en"]
                        reply_zh = reply_data.get("reply_zh", "")
                    else:
                        reply_en = "Sorry, I didn't quite catch that."
                        reply_zh = "抱歉，我没听清。"

                    # 💥 优化点3：对话文本一出来，立刻派发【TTS语音任务】
                    future_tts = executor.submit(
                        self._run_tts_task,
                        reply_en
                    )

                    # ⏳ 等待剩余收尾工作：
                    # 此时【诊断任务】因为是和【对话任务】同时起跑的，现在大概率已经完成了！
                    # 【TTS任务】通常只需几百毫秒，所以这里几乎是秒过。
                    diag_res = future_diag.result()
                    reply_audio = future_tts.result()

                # =========================
                # 数据统合与 UI 刷新
                # =========================
                # 1. 保存诊断结果
                if diag_res:
                    st.session_state.diagnostics[user_index] = diag_res

                # 2. 插入带有语音的完整AI消息
                st.session_state.lingua_history.append({
                    "role": "assistant",
                    "content_en": reply_en,
                    "content_zh": reply_zh,
                    "audio": reply_audio,
                    "played": False
                })

                # 3. 清理状态并刷新页面
                st.session_state.agent_stage = None
                st.session_state.pending_user_text = None

                st.rerun()

    def _run_tts_task(self, reply_en):
        try:
            audio = generate_audio_reply(reply_en, "Cherry")
            return audio
        except Exception as e:
            logger.error(f"TTS失败: {e}")
            return None

    def _run_diag_task(self, user_text, history):
        try:
            diag_res = EnglishAgents.diagnostic_agent(
                user_text,
                history
            )
            return diag_res
        except Exception as e:
            logger.error(f"Diagnostic失败: {e}")
            return None

    def run(self):
        """主入口"""
        st.header("🗣️ 凌云语境 (Lingua-Scholar)")

        # 顶级三大板块 Tab
        tab_dialogue, tab_practice = st.tabs(["💬 对话", "🎯 练习"])

        with tab_dialogue:
            self.render_chat_tab()

        with tab_practice:
            st.subheader("🎯 情景练习 (即将推出)")
            st.write("通过插件式设计，这里未来可以载入：外贸口语、雅思Part2、会议Q&A等特定剧本。")

# ======= 暴露给 main.py 的入口函数 =======
def render_english_module():
    app = EnglishLinguaApp()
    app.run()