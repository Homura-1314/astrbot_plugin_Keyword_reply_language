import random
from astrbot.api.message_components import Record, Plain, At, Face
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.all import *
from astrbot.core.star.context import Context
import json
import os
import re
from astrbot.api.star import Context, Star, register
from astrbot.api.all import Plain
from astrbot.api.message_components import Record  
from astrbot.api.event import filter
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event import MessageChain  
from fuzzywuzzy import fuzz


@register(
    "astrbot_plugin_Keyword_reply_language",
    "关键词语音回复",
    "自动检测消息中的关键词并回复对应的本地语音文件",
    "v1.0.0",
)
class KeywordVoicePlugin(Star):
    def __init__(self, context: Context):  
        super().__init__(context)  
        self.enabled = True
        self.rooms = []
        self.config = context.get_config().get(
            "astrbot_plugin_Keyword_reply_language", {}
        )
        self.keywords = {}
        self.voice_folder = self.config.get(
            "语音文件夹", "./data/plugins/astrbot_plugin_Keyword_reply_language/voices/"
        )
        self.regex_mode = self.config.get("正则表达式模式", False)
        self.case_sensitive = self.config.get("区分大小写", False)
        self.exact_match = self.config.get("精确匹配", False)
        self.reply_chance = self.config.get("回复概率", 1.0)
        self.send_text = self.config.get("同时发送文本", True)
        logger.info(f"文本发送开关状态：{self.send_text}")  

        # 文件路径
        self.keywords_file = (
            "./data/plugins/astrbot_plugin_Keyword_reply_language/keywords.json"
        )
        self.rooms_file = (
            "./data/plugins/astrbot_plugin_Keyword_reply_language/disabled_rooms.json"
        )

        # 创建目录
        os.makedirs(self.voice_folder, exist_ok=True)
        self.load_data()
        logger.info(f"关键词语音回复插件已加载，共 {len(self.keywords)} 个关键词")

    def load_data(self):
        """加载关键词和群组设置"""
        # 加载关键词
        if os.path.exists(self.keywords_file):
            try:
                with open(self.keywords_file, "r", encoding="utf-8") as f:
                    self.keywords = json.load(f)  # 直接加载整个JSON文件
                logger.info(f"已加载 {len(self.keywords)} 个关键词")
            except Exception as e:
                logger.error(f"加载关键词文件失败: {e}")
                self.keywords = {}
                self.save_keywords()
        else:
            logger.info(f"关键词文件不存在，已创建空文件")
            self.keywords = {}
            self.save_keywords()

        # 加载禁用群组
        if os.path.exists(self.rooms_file):
            try:
                with open(self.rooms_file, "r", encoding="utf-8") as f:
                    self.rooms = json.load(f)
                logger.info(f"已加载 {len(self.rooms)} 个禁用群组")
            except Exception as e:
                logger.error(f"加载禁用群组文件失败: {e}")
                self.rooms = []
                self.save_rooms()
        else:
            logger.info(f"禁用群组文件不存在，已创建空文件")
            self.rooms = []
            self.save_rooms()

    def save_keywords(self):
        """保存关键词到文件（自动处理子关键词字段）"""
        try:
            with open(self.keywords_file, "w", encoding="utf-8") as f:
                json.dump(self.keywords, f, ensure_ascii=False, indent=2)
            logger.info(f"关键词保存成功（含 {len(self.keywords)} 个主关键词）")
        except Exception as e:
            logger.error(f"保存失败: {e}")

    def save_rooms(self):
        """保存禁用群组到文件"""
        try:
            with open(self.rooms_file, "w", encoding="utf-8") as f:
                json.dump(self.rooms, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(self.rooms)} 个禁用群组")
        except Exception as e:
            logger.error(f"保存禁用群组文件失败: {e}")

    @filter.command("kwvoice")
    async def switch(self, event: AstrMessageEvent):
        """开关插件"""
        user_id = event.get_sender_id()
        room = event.get_group_id()

        if room in self.rooms:
            self.rooms.remove(room)
            chain = [At(qq=user_id), Plain(f"\n本群关键词语音回复已启用"), Face(id=337)]
        else:
            self.rooms.append(room)
            chain = [At(qq=user_id), Plain(f"\n本群关键词语音回复已禁用"), Face(id=337)]

        self.save_rooms()
        yield event.chain_result(chain)

    @filter.command("文本开关")
    async def toggle_text(self, event: AstrMessageEvent):
        """开关同时发送文本"""
        user_id = event.get_sender_id()
        self.send_text = not self.send_text
        self.config["同时发送文本"] = self.send_text

        if self.send_text:
            chain = [At(qq=user_id), Plain(f"\n文本已经启动"), Face(id=337)]
        else:
            chain = [At(qq=user_id), Plain(f"\n文本已经关闭"), Face(id=337)]

        yield event.chain_result(chain)

    @filter.command_group("kv")
    async def keyword_voice(self, event: AstrMessageEvent):
        """关键词语音回复指令组"""
        pass

    @keyword_voice.command("add")
    async def add_keyword(self, event: AstrMessageEvent, keyword: str, voice_file: str):
        """添加关键词语音回复
        指令格式: /kv add [关键词] [语音文件名]"""
        voice_path = os.path.join(self.voice_folder, voice_file)

        # 检查语音文件是否存在
        if not os.path.exists(voice_path):
            existing_files = os.listdir(self.voice_folder)
            yield event.plain_result(
                f"错误：语音文件 {voice_file} 不存在。目录下现有文件：{', '.join(existing_files)}"
            )
            return

        # 添加或更新关键词
        if keyword in self.keywords:
            yield event.plain_result(f"关键词「{keyword}」已更新 → {voice_file}")
        else:
            yield event.plain_result(f"已添加关键词「{keyword}」→ {voice_file}")

        self.keywords[keyword] = {
            "voice": voice_file,
            "text": "",  # 文本内容留空
        }
        self.save_keywords()

    @keyword_voice.command("del")
    async def del_keyword(self, event: AstrMessageEvent, keyword: str):
        """删除关键词
        /kv del 关键词"""
        if keyword in self.keywords:
            del self.keywords[keyword]
            yield event.plain_result(f"已删除关键词「{keyword}」")
            self.save_keywords()
        else:
            yield event.plain_result(f"关键词「{keyword}」不存在")

    @keyword_voice.command("list")
    async def list_keywords(self, event: AstrMessageEvent):
        """列出所有主关键词及其子关键词"""
        if not self.keywords:
            yield event.plain_result("当前无关键词")
            return

        result = "📜 关键词列表：\n"
        for idx, (main_kw, data) in enumerate(self.keywords.items(), 1):
            result += f"{idx}. 主关键词：{main_kw}\n"
            result += f"   - 语音文件：{data['voice']}\n"
            result += f"   - 关联文本：{data.get('text', '无')}\n"
            sub_keywords = data.get("sub_keywords", [])  # 安全获取子关键词
            result += f"   - 子关键词：{', '.join(sub_keywords)}\n"  # 正确闭合

        yield event.plain_result(result.strip())

    @keyword_voice.command("regex")
    async def toggle_regex(self, event: AstrMessageEvent):
        """切换正则表达式模式
        /kv regex"""
        self.regex_mode = not self.regex_mode
        self.config["正则表达式模式"] = self.regex_mode

        if self.regex_mode:
            yield event.plain_result("已启用正则表达式模式")
        else:
            yield event.plain_result("已禁用正则表达式模式")

    @keyword_voice.command("case")
    async def toggle_case_sensitive(self, event: AstrMessageEvent):
        """切换大小写敏感
        /kv case"""
        self.case_sensitive = not self.case_sensitive
        self.config["区分大小写"] = self.case_sensitive

        if self.case_sensitive:
            yield event.plain_result("已启用大小写敏感")
        else:
            yield event.plain_result("已禁用大小写敏感")

    @keyword_voice.command("exact")
    async def toggle_exact_match(self, event: AstrMessageEvent):
        """切换精确匹配
        /kv exact"""
        self.exact_match = not self.exact_match
        self.config["精确匹配"] = self.exact_match

        if self.exact_match:
            yield event.plain_result("已启用精确匹配")
        else:
            yield event.plain_result("已禁用精确匹配")

    @keyword_voice.command("chance")
    async def set_reply_chance(self, event: AstrMessageEvent, chance: float):
        """设置回复概率
        /kv chance 0.5 (0.0-1.0)"""
        if chance < 0.0 or chance > 1.0:
            yield event.plain_result("概率必须在 0.0-1.0 之间")
            return

        self.reply_chance = chance
        self.config["回复概率"] = chance
        yield event.plain_result(f"回复概率已设置为 {chance*100:.0f}%")

    @keyword_voice.command("text")
    async def set_keyword_text(self, event: AstrMessageEvent, keyword: str, text: str):
        """设置关键词的全局文本内容（所有群组和私聊生效）"""
        if keyword not in self.keywords:
            yield event.plain_result(f"关键词「{keyword}」不存在")
            return

        self.keywords[keyword]["text"] = text  # 直接更新全局文本
        self.save_keywords()
        yield event.plain_result(f"已设置关键词「{keyword}」的全局文本内容")

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        logger.info(
            f"收到消息类型：{event.get_message_type()}, 内容：{event.message_str}"
        )

        def clean_text(text: str) -> str:
            """清洗文本：保留中文、字母、数字，移除其他字符"""
            cleaned = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)
            return cleaned.lower()

        # 处理私聊消息
        if event.get_message_type() == "private":
            message = event.message_str.strip()
        else:
            # 群聊检查是否禁用
            room = event.get_group_id()
            if room in self.rooms:
                logger.info(f"群组 {room} 已禁用插件")
                return
            message = event.message_str.strip()

        if not message or random.random() > self.reply_chance:
            return

        # 清洗消息
        message_check = clean_text(message)
        logger.info(f"清洗后的消息内容: {message_check}")

        # --- 匹配逻辑修复 ---
        matched_keyword = None
        keyword_data = None

        if self.regex_mode:
            for keyword, data in self.keywords.items():
                keyword_cleaned = clean_text(keyword)
                try:
                    flags = re.IGNORECASE if not self.case_sensitive else 0
                    if re.search(keyword, message, flags=flags):
                        matched_keyword = keyword
                        keyword_data = data
                        break
                except re.error as e:
                    logger.error(f"正则表达式错误：{keyword} - {e}")
        else:
            # 遍历关键词及其数据
            for keyword, data in self.keywords.items():
                keyword_cleaned = clean_text(keyword)
                matched = False  # 标志变量

                # 1. 检查子关键词
                sub_keywords = data.get("sub_keywords", [])
                for sub_kw in sub_keywords:
                    sub_cleaned = clean_text(sub_kw)
                    if sub_cleaned in message_check:
                        matched_keyword = keyword
                        keyword_data = data
                        matched = True
                        break  # 跳出子关键词循环

                if matched:
                    break  # 跳出外层循环

                # 2. 模糊匹配主关键词
                similarity = fuzz.partial_ratio(keyword_cleaned, message_check)
                if similarity > 50: //匹配的模糊概率
                    matched_keyword = keyword
                    keyword_data = data
                    logger.info(f"模糊匹配成功：相似度 {similarity}%")
                    break  # 跳出外层循环

        if matched_keyword and keyword_data:
            voice_path = os.path.join(self.voice_folder, keyword_data["voice"])
            logger.info(f"语音文件路径：{voice_path}")

            if not os.path.exists(voice_path):
                logger.error(f"语音文件不存在：{voice_path}")
                return

        if matched_keyword and keyword_data:
            logger.info(
                f"匹配到关键词：{matched_keyword}, 文本内容：{keyword_data.get('text')}"
            )

        # --- 发送逻辑 ---
        if matched_keyword and keyword_data:
            voice_path = os.path.join(self.voice_folder, keyword_data["voice"])
            text_content = keyword_data.get("text", "")
            # 发送语音
            if os.path.exists(voice_path):
                try:
                    voice_chain = MessageChain([Record.fromFileSystem(voice_path)])
                    await event.send(voice_chain)
                    logger.info(f"语音发送成功：{voice_path}")
                except Exception as e:
                    logger.error(f"语音发送失败: {e}")
            # 发送文本
            if event.message_str and text_content:
                try:
                    text_chain = MessageChain([Plain(text_content)])
                    await event.send(text_chain)
                    logger.info(f"文本发送成功：{text_content}")
                except Exception as e:
                    logger.error(f"文本发送失败: {e}")

            event.stop_event()  # 结束事件传播


    '''
    @keyword_voice.command("subadd")
    async def add_sub_keyword(self, event: AstrMessageEvent, main_keyword: str, sub_keyword: str):

        """添加子关键词main_keyword为[主关键词]sub_keyword为[子关键词]"""
        raw_message = event.message_str.strip()
        logger.info(f"原始指令内容：{raw_message}")

        # 分割参数（保留斜杠）
        parts = raw_message.split()
        logger.info(f"分割后的参数列表：{parts}")

        # 校验指令格式：/kv subadd 主关键词 子关键词
        if len(parts) < 4 or parts[0] != "/kv" or parts[1] != "subadd":
            yield event.plain_result("❌ 格式错误！正确格式：/kv subadd [主关键词] [子关键词]")
            return

        main_keyword = parts[2]
        sub_keyword = parts[3]

        # 检查主关键词是否存在
        if main_keyword not in self.keywords:
            yield event.plain_result(f"❌ 主关键词「{main_keyword}」不存在")
            return

        # 添加子关键词
        data = self.keywords[main_keyword]
        sub_keywords = data.get("sub_keywords", [])

        if sub_keyword in sub_keywords:
            yield event.plain_result(f"❌ 子关键词「{sub_keyword}」已存在")
        else:
            sub_keywords.append(sub_keyword)
            data["sub_keywords"] = sub_keywords
            self.save_keywords()
            logger.info(f"✅ 已添加子关键词：{main_keyword} → {sub_keyword}")
            yield event.plain_result(f"✅ 已为「{main_keyword}」添加子关键词 → {sub_keyword}")
    '''
