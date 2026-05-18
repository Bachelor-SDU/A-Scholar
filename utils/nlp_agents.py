# utils/nlp_agents.py
import json
from utils.llm_client import get_llm_response


class EnglishAgents:
    """封装所有英语相关的智能体能力"""

    @staticmethod
    def chat_agent(history):
        """主聊大脑：同时输出英文回复和中文翻译的 JSON"""
        sys_prompt = {
            "role": "system",
            "content": """You are a friendly native English speaker. Keep the conversation natural. 
            You MUST output your response strictly in JSON format containing both your English reply and its natural Chinese translation.
            Schema: {"reply_en": "Your short English reply (1-2 sentences).", "reply_zh": "对应的中文翻译"}"""
        }
        messages = [sys_prompt] + history
        # 强制启用 json_mode
        return get_llm_response(messages, json_mode=True)

    @staticmethod
    def hint_agent(history):
        """提示大脑：生成3个回复建议 (返回JSON格式)"""
        prompt = "Based on the conversation history, provide 3 different short English reply suggestions for the user (e.g., agreeing, disagreeing, asking a detail). Output strictly as JSON: {'hints': ['Hint 1', 'Hint 2', 'Hint 3']}"
        messages = history + [{"role": "user", "content": prompt}]
        return get_llm_response(messages, json_mode=True)

    @staticmethod
    def diagnostic_agent(user_text, history):
        """诊断大脑：引入上下文机制，避免误判短语"""

        # 提取最近的3轮对话作为上下文
        context_str = ""
        for m in history[-3:]:
            role = "AI" if m["role"] == "assistant" else "User"
            # 处理因为ChatAgent改版导致的字段变化
            content = m.get("content_en", m.get("content", ""))
            context_str += f"{role}: {content}\n"

        prompt = f"""
        Analyze the user's latest English reply IN THE CONTEXT of the conversation.

        [Conversation Context]:
        {context_str}

        [User's Latest Reply]: "{user_text}"

        Rules:
        1. Context Matters: If the user's reply is a natural, grammatically acceptable short answer (e.g., "Apple", "Yes I do", "Not bad") given the AI's question, set "has_error" to false! Do NOT complain about missing subjects/verbs if it's normal conversational ellipsis.
        2. Output strictly in JSON format.

        Schema:
        {{
            "translation": "用户这句话的中文翻译",
            "native_eval": "结合上下文，母语者对这句话的评价(如: 回答很自然，或者略显生硬)",
            "has_error": true/false,
            "correction": {{
                "old_text": "需要被替换的错误片段(没有则为空)",
                "new_text": "正确的片段",
                "full_sentence": "完整的正确句子",
                "translation": "正确句子的中文翻译"
            }},
            "alternatives": {{
                "general": {{"text": "...", "trans": "...", "analysis": "..."}},
                "idiomatic": {{"text": "...", "trans": "...", "analysis": "..."}},
                "academic": {{"text": "...", "trans": "...", "analysis": "..."}}
            }}
        }}
        """
        result = get_llm_response([{"role": "user", "content": prompt}], json_mode=True)

        # 保底机制：如果大模型崩溃或解析失败，返回一个默认的安全字典，防止前端崩溃
        if not result:
            result = {
                "translation": "解析失败",
                "native_eval": "网络拥堵，本次未完成评价。",
                "has_error": False,
                "correction": {"old_text": "", "new_text": "", "full_sentence": user_text, "translation": ""},
                "alternatives": {
                    "general": {"text": "N/A", "trans": "N/A", "analysis": "无"},
                    "idiomatic": {"text": "N/A", "trans": "N/A", "analysis": "无"},
                    "academic": {"text": "N/A", "trans": "N/A", "analysis": "无"}
                }
            }
        return result
    @staticmethod
    def dictionary_agent(word):
        """词典大脑：查词器 (返回JSON格式)"""
        prompt = f"""
        Look up the word/phrase: "{word}". Output strictly in JSON:
        {{
            "word": "{word}",
            "uk_phonetic": "英音音标", "us_phonetic": "美音音标",
            "level": "CET4 / CET6 / 考研 / 雅思 (选一个合适的)",
            "meanings": [
                {{"pos": "词性(如 n.)", "def": "中文释义"}}
            ]
        }}
        """
        return get_llm_response([{"role": "user", "content": prompt}], json_mode=True)


class UserDataStore:
    """用户数据管理 (面向对象设计，方便未来接数据库)"""

    def __init__(self, session_state):
        self.state = session_state
        if "favorites" not in self.state: self.state.favorites = {"words": [], "sentences": []}
        if "mistakes" not in self.state: self.state.mistakes = []
        if "vocab_bank" not in self.state: self.state.vocab_bank = set()

    def save_word(self, word_data):
        self.state.favorites["words"].append(word_data)

    def save_sentence(self, text, trans):
        self.state.favorites["sentences"].append({"text": text, "trans": trans})

    def log_mistake(self, original, corrected):
        self.state.mistakes.append({"original": original, "corrected": corrected})