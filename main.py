# main.py

import asyncio
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, StarTools
from astrbot.core import AstrBotConfig
from astrbot.core.message.components import At, Image, Json, Video, Plain
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from .core.arbiter import ArbiterContext, EmojiLikeArbiter
from .core.clean import CacheCleaner
from .core.debounce import Debouncer
from .core.download import Downloader
from .core.parsers import BaseParser, BilibiliParser
from .core.render import Renderer
from .core.sender import MessageSender
from .core.utils import extract_json_url


class ParserPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.config = config
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # 初始化默认配置
        if "ignore_prefixes" not in self.config:
            self.config["ignore_prefixes"] = ["/ytd"]
        if "ytd_progress_report_interval" not in self.config:
            self.config["ytd_progress_report_interval"] = 0
        if "ytd_save_dir" not in self.config:
            self.config["ytd_save_dir"] = ""
        if "ytd_delete_after_send" not in self.config:
            self.config["ytd_delete_after_send"] = True
        
        # 新增白名单机制默认配置
        if "parsing_mode" not in self.config:
            self.config["parsing_mode"] = "白名单"
        if "enabled_sessions" not in self.config:
            self.config["enabled_sessions"] = []
            
        self.config.save_config()

        # 插件数据目录
        self.data_dir: Path = StarTools.get_data_dir("astrbot_plugin_zidongjiexiplusyoutubexiazai")
        config["data_dir"] = str(self.data_dir)

        # 缓存目录
        self.cache_dir: Path = self.data_dir / "cache_dir"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        config["cache_dir"] = str(self.cache_dir)
        self.config.save_config()

        # 关键词 -> Parser 映射
        self.parser_map: dict[str, BaseParser] = {}

        # 关键词 -> 正则 列表
        self.key_pattern_list: list[tuple[str, re.Pattern[str]]] = []

        # 渲染器
        self.renderer = Renderer(config)

        # 下载器
        self.downloader = Downloader(config)

        # 防抖器
        self.debouncer = Debouncer(config)

        # 仲裁器
        self.arbiter = EmojiLikeArbiter()

        # 消息发送器
        self.sender = MessageSender(config, self.renderer)

        # 缓存清理器
        self.cleaner = CacheCleaner(self.context, self.config)
        
        # ytdlp 会话状态
        self.ytdlp_sessions: dict[str, dict] = {}
        # 正在进行的 ytdlp 任务
        self.active_ytd_tasks: dict[str, dict] = {} # user_key -> {status, progress_str}

    async def initialize(self):
        """加载、重载插件时触发"""
        # 加载x渲染器资源
        await asyncio.to_thread(Renderer.load_resources)
        # 注册解析器
        self._register_parser()

    async def terminate(self):
        """插件卸载时触发"""
        # 关下载器里的会话
        await self.downloader.close()
        # 关所有解析器里的会话 (去重后的实例)
        unique_parsers = set(self.parser_map.values())
        for parser in unique_parsers:
            await parser.close_session()
        # 关缓存清理器
        await self.cleaner.stop()

    def _register_parser(self):
        """注册解析器"""
        # 获取所有解析器
        all_subclass = BaseParser.get_all_subclass()
        # 过滤掉禁用的平台
        enabled_classes = [
            _cls
            for _cls in all_subclass
            if _cls.platform.display_name in self.config["enable_platforms"]
        ]
        # 启用的平台
        platform_names = []
        for _cls in enabled_classes:
            parser = _cls(self.config, self.downloader)
            platform_names.append(parser.platform.display_name)
            for keyword, _ in _cls._key_patterns:
                self.parser_map[keyword] = parser
        logger.info(f"启用平台: {'、'.join(platform_names)}")

        # 关键词-正则对，一次性生成并排序
        patterns: list[tuple[str, re.Pattern[str]]] = [
            (kw, re.compile(pt) if isinstance(pt, str) else pt)
            for cls in enabled_classes
            for kw, pt in cls._key_patterns
        ]
        # 长关键词优先
        patterns.sort(key=lambda x: -len(x[0]))
        keywords = [kw for kw, _ in patterns]
        logger.debug(f"关键词-正则对已生成：{keywords}")
        self.key_pattern_list = patterns

    def _get_parser_by_type(self, parser_type):
        for parser in self.parser_map.values():
            if isinstance(parser, parser_type):
                return parser
        raise ValueError(f"未找到类型为 {parser_type} 的 parser 实例")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """消息的统一入口"""
        # 防止与 /ytd 指令或其他配置的前缀冲突
        msg_str = event.message_str.strip()
        ignore_prefixes = self.config.get("ignore_prefixes", ["/ytd"])
        for prefix in ignore_prefixes:
            if msg_str.startswith(prefix):
                return

        # 优先处理 ytdlp 会话
        try:
            user_key = f"{event.unified_msg_origin}_{event.get_sender_id()}"
            if user_key in self.ytdlp_sessions:
                await self._handle_ytdlp_selection(event, user_key)
                return
        except Exception:
            pass

        umo = event.unified_msg_origin
        mode = self.config.get("parsing_mode", "白名单")

        if mode == "黑名单":
            # 黑名单模式：如果在禁用列表中，则不解析
            if umo in self.config.get("disabled_sessions", []):
                return
        else:
            # 白名单模式（默认）：如果不在启用列表中，则不解析
            if umo not in self.config.get("enabled_sessions", []):
                return

        # 消息链
        chain = event.get_messages()
        if not chain:
            return

        seg1 = chain[0]
        text = event.message_str
        
        # 卡片解析：解析Json组件，提取URL
        if isinstance(seg1, Json):
            text = extract_json_url(seg1.data)
            logger.debug(f"解析Json组件: {text}")

        if not text:
            return

        self_id = event.get_self_id()

        # 指定机制：专门@其他bot的消息不解析
        if isinstance(seg1, At) and str(seg1.qq) != self_id:
            return

        # 核心匹配逻辑 ：关键词 + 正则双重判定，汇集了所有解析器的正则对。
        keyword: str = ""
        searched: re.Match[str] | None = None
        for kw, pat in self.key_pattern_list:
            if kw not in text:
                continue
            if m := pat.search(text):
                keyword, searched = kw, m
                break
        if searched is None:
            return
        logger.debug(f"匹配结果: {keyword}, {searched}")

        # 仲裁机制
        if isinstance(event, AiocqhttpMessageEvent) and not event.is_private_chat():
            raw = event.message_obj.raw_message
            if not isinstance(raw, dict):
                logger.warning(f"Unexpected raw_message type: {type(raw)}")
                return
            is_win = await self.arbiter.compete(
                bot=event.bot,
                ctx=ArbiterContext(
                    message_id=int(raw["message_id"]),
                    msg_time=int(raw["time"]),
                    self_id=int(raw["self_id"]),
                ),
            )
            if not is_win:
                logger.debug("Bot在仲裁中输了, 跳过解析")
                return
            logger.debug("Bot在仲裁中胜出, 准备解析...")

        # 基于link防抖
        link = searched.group(0)
        if self.debouncer.hit_link(umo, link):
            logger.warning(f"[链接防抖] 链接 {link} 在防抖时间内，跳过解析")
            return

        # 解析
        parse_res = await self.parser_map[keyword].parse(keyword, searched)

        # 基于资源ID防抖
        resource_id = parse_res.get_resource_id()
        if self.debouncer.hit_resource(umo, resource_id):
            logger.warning(f"[资源防抖] 资源 {resource_id} 在防抖时间内，跳过发送")
            return

        # 发送
        await self.sender.send_parse_result(event, parse_res)

    @filter.command("开启解析")
    async def open_parser(self, event: AstrMessageEvent):
        """开启当前会话的解析"""
        umo = event.unified_msg_origin
        mode = self.config.get("parsing_mode", "白名单")
        
        if mode == "黑名单":
            sessions = self.config.get("disabled_sessions", [])
            if umo in sessions:
                sessions.remove(umo)
                self.config["disabled_sessions"] = sessions
                self.config.save_config()
                yield event.plain_result("解析已开启")
            else:
                yield event.plain_result("解析已开启，无需重复开启")
        else:
            # 白名单模式
            sessions = self.config.get("enabled_sessions", [])
            if umo not in sessions:
                sessions.append(umo)
                self.config["enabled_sessions"] = sessions
                self.config.save_config()
                yield event.plain_result("解析已开启")
            else:
                yield event.plain_result("解析已开启，无需重复开启")

    @filter.command("关闭解析")
    async def close_parser(self, event: AstrMessageEvent):
        """关闭当前会话的解析"""
        umo = event.unified_msg_origin
        mode = self.config.get("parsing_mode", "白名单")
        
        if mode == "黑名单":
            sessions = self.config.get("disabled_sessions", [])
            if umo not in sessions:
                sessions.append(umo)
                self.config["disabled_sessions"] = sessions
                self.config.save_config()
                yield event.plain_result("解析已关闭")
            else:
                yield event.plain_result("解析已关闭，无需重复关闭")
        else:
            # 白名单模式
            sessions = self.config.get("enabled_sessions", [])
            if umo in sessions:
                sessions.remove(umo)
                self.config["enabled_sessions"] = sessions
                self.config.save_config()
                yield event.plain_result("解析已关闭")
            else:
                yield event.plain_result("解析已关闭，无需重复关闭")
    
    @filter.command("ytd")
    async def ytd_cmd(self, event: AstrMessageEvent, url: str = ""):
        """yt-dlp 手动选格式下载。如果不加参数，查询当前进度。"""
        user_key = f"{event.unified_msg_origin}_{event.get_sender_id()}"

        if not url:
            # 查询进度
            if user_key in self.active_ytd_tasks:
                task_info = self.active_ytd_tasks[user_key]
                progress = task_info.get("progress_str", "正在准备...")
                yield event.plain_result(f"当前下载进度:\n{progress}")
            else:
                yield event.plain_result("当前没有正在进行的下载任务，请使用 /ytd <url> 开始下载")
            return

        yield event.plain_result("正在获取视频格式，请稍候...")
        
        cookie_path = None
        if self.config.get("ytb_cookies_file"):
            p = Path(self.config["ytb_cookies_file"])
            if p.is_file():
                cookie_path = p
        
        try:
            formats = await self.downloader.get_ytdlp_formats(url, cookiefile=cookie_path)
        except Exception as e:
            yield event.plain_result(f"获取格式失败: {e}")
            return
            
        if not formats:
            yield event.plain_result("未找到可用格式")
            return
            
        # 展示前 15 个格式（通常是最好的）
        display_formats = formats[:15]
        
        options = []
        msg_lines = ["请回复序号选择下载格式 (20秒内):"]
        
        for i, f in enumerate(display_formats):
            size_mb = 0
            if f['filesize']:
                size_mb = f['filesize'] / 1024 / 1024
            
            note = f['note']
            res = f['resolution']
            ext = f['ext']
            # f['vcodec'] maybe meaningful
            desc = f"{i+1}. [{ext}] {res} {note} ({size_mb:.1f}MB)"
            msg_lines.append(desc)
            options.append(f)
            
        self.ytdlp_sessions[user_key] = {
            "url": url,
            "options": options,
            "event": event 
        }
        
        # 启动超时倒计时
        asyncio.create_task(self._ytdlp_timeout(user_key, event))
        
        yield event.plain_result("\n".join(msg_lines))

    async def _ytdlp_timeout(self, key: str, event: AstrMessageEvent):
        await asyncio.sleep(20)
        if key in self.ytdlp_sessions:
            del self.ytdlp_sessions[key]
            await event.send(event.plain_result("选择超时，已取消下载"))

    async def _handle_ytdlp_selection(self, event: AstrMessageEvent, key: str):
        text = event.message_str.strip()
        
        # 无论输入啥，先获取session
        session = self.ytdlp_sessions[key]
        
        if not text.isdigit():
            # 如果不是数字，可能用户只想闲聊？但在 session 模式下默认拦截所有
            # 这里选择拦截并提示，然后清除 session
            del self.ytdlp_sessions[key] 
            await event.send(event.plain_result("输入无效，已退出选择"))
            return
            
        idx = int(text) - 1
        options = session["options"]
        
        if idx < 0 or idx >= len(options):
            del self.ytdlp_sessions[key] 
            await event.send(event.plain_result("序号超出范围，已退出选择"))
            return
            
        # 选对了
        del self.ytdlp_sessions[key] # 立即清除防止重复
        
        selected = options[idx]
        url = session["url"]
        
        await event.send(event.plain_result(f"已选择: {selected['resolution']}，任务已后台启动。请耐心等待，使用 ytd 查询进度。"))
        
        # 启动后台任务
        asyncio.create_task(self._download_and_send(event, key, url, selected["format_id"]))

    async def _download_and_send(self, event: AstrMessageEvent, user_key: str, url: str, format_id: str):
        """后台下载并发送"""
        self.active_ytd_tasks[user_key] = {
            "progress_str": "准备下载...", 
            "status": "downloading",
            "last_report_time": 0
        }
        
        report_interval = self.config.get("ytd_progress_report_interval", 0)
        
        # 获取主循环
        loop = asyncio.get_running_loop()
        
        def progress_hook(d):
            task_data = self.active_ytd_tasks.get(user_key)
            if not task_data: return

            if d['status'] == 'downloading':
                percent = d.get('_percent_str', 'N/A').strip()
                speed = d.get('_speed_str', 'N/A').strip()
                eta = d.get('_eta_str', 'N/A').strip()
                prog_str = f"下载中: {percent} | 速度: {speed} | 剩余时间: {eta}"
                task_data["progress_str"] = prog_str
                
                # 自动汇报进度
                now = time.time()
                if report_interval > 0 and (now - task_data["last_report_time"]) >= report_interval:
                    task_data["last_report_time"] = now
                    # 线程安全调用
                    asyncio.run_coroutine_threadsafe(event.send(event.plain_result(prog_str)), loop)

            elif d['status'] == 'finished':
                task_data["progress_str"] = "下载完成，正在转码/合并..."
                if report_interval > 0:
                     asyncio.run_coroutine_threadsafe(event.send(event.plain_result("下载阶段完成，开始转码/合并...")), loop)

        cookie_path = None
        if self.config.get("ytb_cookies_file"):
            p = Path(self.config["ytb_cookies_file"])
            if p.is_file():
                cookie_path = p
        
        # 自定义下载目录
        custom_dir = None
        if self.config.get("ytd_save_dir"):
            custom_dir = Path(self.config["ytd_save_dir"])
            
        path = None
        try:
            path = await self.downloader.download_ytdlp_format(
                url, 
                format_id, 
                cookiefile=cookie_path, 
                download_hook=progress_hook,
                custom_dir=custom_dir
            )
            
            self.active_ytd_tasks[user_key]["progress_str"] = "发送中..."
            
            # 尝试发送，忽略发送过程中的超时错误
            try:
                await event.send(event.chain_result([Video(str(path))]))
                self.active_ytd_tasks[user_key]["progress_str"] = "发送完成"
            except Exception as e:
                logger.warning(f"Send video failed (possibly timeout, but upload likely continues): {e}")
                self.active_ytd_tasks[user_key]["progress_str"] = f"发送可能已超时: {e}"
            
            # 发送后删除（默认开启）
            delete_after = self.config.get("ytd_delete_after_send", True)
            if delete_after and path and path.exists():
                path.unlink()
                
        except Exception as e:
            logger.exception("Manual ytdlp download failed")
            await event.send(event.plain_result(f"下载失败: {e}"))
        finally:
            if user_key in self.active_ytd_tasks:
                del self.active_ytd_tasks[user_key]

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("登录B站", alias={"blogin", "登录b站"})
    async def login_bilibili(self, event: AstrMessageEvent):
        """扫码登录B站"""
        parser: BilibiliParser = self._get_parser_by_type(BilibiliParser)  # type: ignore
        qrcode = await parser.login_with_qrcode()
        yield event.chain_result([Image.fromBytes(qrcode)])
        async for msg in parser.check_qr_state():
            yield event.plain_result(msg)
