import random
from astrbot.api.message_components import Record, Plain, At, Face
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.all import *
from astrbot.core.star.context import Context
import json
import os
import re
from typing import Dict, List
from astrbot.core.star import Star
from astrbot.api.all import Plain
from astrbot.api.message_components import Record  # 仅保留必要的导入
from astrbot.api.event import filter
from astrbot.core.star.filter.platform_adapter_type import PlatformAdapterType
from astrbot.core.star.filter.event_message_type import EventMessageType
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event import MessageChain  # 确保导入 MessageChain

@register(
    "astrbot_plugin_Keyword_reply_language",
    "关键词语音回复",
    "自动检测消息中的关键词并回复对应的本地语音文件",
    "v1.0.0",
)
class KeywordVoicePlugin(Star):
    def __init__(self, context: Context):  # 仅接收 context
        super().__init__(context)  # 父类构造函数仅需 context
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
        self.send_text = self.config.get("同时发送文本", False)

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
                with open(self.keywords_file, 'r', encoding='utf-8') as f:
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
    
        # 加载禁用群组（同理修改）
        if os.path.exists(self.rooms_file):
            try:
                with open(self.rooms_file, 'r', encoding='utf-8') as f:
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
        """保存关键词到文件"""
        try:
            with open(self.keywords_file, 'w', encoding='utf-8') as f:
                json.dump(self.keywords, f, ensure_ascii=False, indent=2)  # 使用缩进美化格式
            logger.info(f"已保存 {len(self.keywords)} 个关键词")
        except Exception as e:
            logger.error(f"保存关键词文件失败: {e}")
            
    def save_rooms(self):
        """保存禁用群组到文件"""
        try:
            with open(self.rooms_file, 'w', encoding='utf-8') as f:
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
            chain = [
                At(qq=user_id),
                Plain(f"\n本群关键词语音回复已启用"),
                Face(id=337)
            ]
        else:
            self.rooms.append(room)
            chain = [
                At(qq=user_id),
                Plain(f"\n本群关键词语音回复已禁用"),
                Face(id=337)
            ]

        self.save_rooms()
        yield event.chain_result(chain)

    @filter.command("文本开关")
    async def toggle_text(self, event: AstrMessageEvent):
        """开关同时发送文本"""
        user_id = event.get_sender_id()
        self.send_text = not self.send_text
        self.config['同时发送文本'] = self.send_text

        if self.send_text:
            chain = [
                At(qq=user_id),
                Plain(f"\n文本已经启动"),
                Face(id=337)
            ]
        else:
            chain = [
                At(qq=user_id),
                Plain(f"\n文本已经关闭"),
                Face(id=337)
            ]

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
        "text": ""  # 文本内容留空（若不需要可删除此行）
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
        """列出所有关键词
        /kv list"""
        if not self.keywords:
            yield event.plain_result("暂无关键词")
            return

        result = "当前关键词语音列表：\n"
        for i, (keyword, data) in enumerate(self.keywords.items(), 1):
            voice_file = data["voice"]
            text = data.get("text", "")
            if text:
                text_preview = text[:15] + "..." if len(text) > 15 else text
                result += f"{i}. 「{keyword}」→ {voice_file} ({text_preview})\n"
            else:
                result += f"{i}. 「{keyword}」→ {voice_file}\n"

        yield event.plain_result(result.strip())

    @keyword_voice.command("regex")
    async def toggle_regex(self, event: AstrMessageEvent):
        """切换正则表达式模式
        /kv regex"""
        self.regex_mode = not self.regex_mode
        self.config['正则表达式模式'] = self.regex_mode

        if self.regex_mode:
            yield event.plain_result("已启用正则表达式模式")
        else:
            yield event.plain_result("已禁用正则表达式模式")

    @keyword_voice.command("case")
    async def toggle_case_sensitive(self, event: AstrMessageEvent):
        """切换大小写敏感
        /kv case"""
        self.case_sensitive = not self.case_sensitive
        self.config['区分大小写'] = self.case_sensitive

        if self.case_sensitive:
            yield event.plain_result("已启用大小写敏感")
        else:
            yield event.plain_result("已禁用大小写敏感")

    @keyword_voice.command("exact")
    async def toggle_exact_match(self, event: AstrMessageEvent):
        """切换精确匹配
        /kv exact"""
        self.exact_match = not self.exact_match
        self.config['精确匹配'] = self.exact_match

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
        self.config['回复概率'] = chance
        yield event.plain_result(f"回复概率已设置为 {chance*100:.0f}%")

    @keyword_voice.command("text")
    async def set_keyword_text(self, event: AstrMessageEvent, keyword: str, text: str):
        """设置关键词的文本内容
        /kv text 关键词 文本内容"""
        if keyword not in self.keywords:
            yield event.plain_result(f"关键词「{keyword}」不存在")
            return

        self.keywords[keyword]["text"] = text
        self.save_keywords()
        yield event.plain_result(f"已设置关键词「{keyword}」的文本内容")

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        # 检查群组是否禁用
        room = event.get_group_id()
        if room in self.rooms:
            return

        # 直接获取消息文本（兼容 aiocqhttp）
        message = event.message_str.strip()
        if not message:
            return

        # 随机概率判定
        if random.random() > self.reply_chance:
            return

        # --- 修复：添加完整的关键词匹配逻辑 ---
        matched_keyword = None
        keyword_data = None

        if self.regex_mode:
            for keyword, data in self.keywords.items():
                try:
                    flags = re.IGNORECASE if not self.case_sensitive else 0
                    if re.search(keyword, message, flags=flags):
                        matched_keyword = keyword
                        keyword_data = data
                        break
                except re.error as e:
                    logger.error(f"正则表达式错误：{keyword} - {e}")
        else:
            message_check = message if self.case_sensitive else message.lower()
            for keyword, data in self.keywords.items():
                keyword_check = keyword if self.case_sensitive else keyword.lower()
                if self.exact_match:
                    if message_check == keyword_check:
                        matched_keyword = keyword
                        keyword_data = data
                        break
                else:
                    if keyword_check in message_check:
                        matched_keyword = keyword
                        keyword_data = data
                        break

        if matched_keyword and keyword_data:
            voice_file = keyword_data["voice"]
            voice_path = os.path.join(self.voice_folder, voice_file)
            logger.info(f"语音文件路径：{voice_path}")

            if not os.path.exists(voice_path):
                logger.error(f"语音文件不存在：{voice_path}")
                return

            try:
                # 正确构建消息链
                voice_chain = MessageChain([Record.fromFileSystem(voice_path)])
                await event.send(voice_chain)
                logger.info("语音消息发送成功")
            except Exception as e:
                logger.error(f"发送语音失败：{e}")
