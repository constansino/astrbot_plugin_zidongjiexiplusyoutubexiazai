# astrbot_plugin_zidongjiexiplusyoutubexiazai

> 本项目基于 [astrbot_plugin_parser](https://github.com/Zhalslar/astrbot_plugin_parser) 开发，增强了 YouTube 下载功能并添加了多种管理特性。

一个功能强大的链接解析器，支持 YouTube, Bilibili, Instagram, Twitter 等多个平台，支持登录。在此基础上，本项目重点增强了 YouTube 下载体验和插件管理功能。

## ✨ 新增功能特性

### 🛠️ YouTube 下载修复与增强
- **修复 HLS 下载失败**：通过强制使用 DASH 协议 (`bv*+ba/b`) 解决了官方版本中出现的 "empty file" 和分片下载错误。
- **环境补全**：内置 Deno 运行时支持，解决了 `yt-dlp` 在新版 YouTube 验证中的依赖问题。
- **Cookie 支持**：完善了 Cookie 加载逻辑，支持通过配置文件挂载 `cookies.txt` 以通过 YouTube 登录验证。

### 📥 强大的 /ytd 手动下载指令
- **手动选择画质**：发送 `/ytd <链接>` 即可列出该视频的前 15 种格式（分辨率、大小、编码），回复序号即可下载。
- **后台异步下载**：下载任务在后台运行，不会阻塞 Bot 响应其他消息。
- **进度实时查询**：下载过程中发送 `/ytd` 即可查看当前下载百分比、速度和剩余时间。
- **自动进度汇报**：支持配置 `ytd_progress_report_interval`，每隔 N 秒自动发送进度通知。
- **超时保护优化**：针对大文件上传，优化了超时处理逻辑。如果上传时间过长，Bot 会提示状态但不会报错，确保用户知道任务仍在进行。

### 🛡️ 灵活的解析管理
- **白名单/黑名单模式**：
  - **白名单模式（默认）**：默认不解析任何群的链接，只有执行 `/开启解析` 的群才会生效。
  - **黑名单模式**：默认解析所有群，执行 `/关闭解析` 的群被屏蔽。
  - 可在配置中切换模式 (`parsing_mode`)。
- **自定义忽略前缀**：支持配置 `ignore_prefixes`（默认包含 `/ytd`），遇到指定前缀的消息将跳过自动解析，避免指令冲突。

### ⚙️ 更多自定义配置
- `ytd_save_dir`: 自定义手动下载视频的保存目录。
- `ytd_delete_after_send`: 选项控制是否在发送给用户后自动删除服务器上的文件。

---

## 📦 安装与配置

### 安装
将本插件目录重命名为 `astrbot_plugin_zidongjiexiplusyoutubexiazai` 并放入 `plugins` 目录。

### 配置文件
配置文件位于 `data/plugins/astrbot_plugin_zidongjiexiplusyoutubexiazai/config.json`（首次运行自动生成）。

关键配置项：
```json
{
  "parsing_mode": "白名单",  // 或 "黑名单"
  "ytd_progress_report_interval": 10, // 自动汇报进度间隔（秒），0为关闭
  "ytd_delete_after_send": true, // 发送后删除文件
  "ignore_prefixes": ["/ytd", "不解析"], // 忽略自动解析的前缀
  "ytb_ck": "..." // YouTube Cookie 字符串
}
```

## 🎮 指令列表

| 指令 | 描述 |
| --- | --- |
| `/ytd <链接>` | 获取 YouTube 视频格式列表并选择下载 |
| `/ytd` | 查询当前手动下载任务的进度 |
| `/开启解析` | 将当前会话加入白名单（或移出黑名单） |
| `/关闭解析` | 将当前会话加入黑名单（或移出白名单） |
| `/登录B站` | 扫码登录 Bilibili |

## 🙏 致谢
感谢原作者 [Zhalslar](https://github.com/Zhalslar) 提供的优秀基础项目。
本项目核心代码来自[nonebot-plugin-parser](https://github.com/fllesser/nonebot-plugin-parser)，请前往原仓库给作者点个Star!   

下面是原项目[Zhalslar](https://github.com/Zhalslar) 2026/01/17的md文件 自用记录修改


<div align="center">

![:name](https://count.getloli.com/@astrbot_plugin_parser?name=astrbot_plugin_parser&theme=minecraft&padding=6&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

# astrbot_plugin_parser

_✨ 链接解析器 ✨_  

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![AstrBot](https://img.shields.io/badge/AstrBot-3.4%2B-orange.svg)](https://github.com/Soulter/AstrBot)
[![GitHub](https://img.shields.io/badge/作者-Zhalslar-blue)](https://github.com/Zhalslar)

</div>

## 📖 介绍

当前支持的平台和类型：

| 平台    | 触发的消息形态                    | 视频 | 图集 | 音频 |
| ------- | --------------------------------- | ---- | ---- | ---- |
| B 站    | av 号/BV 号/链接/短链/卡片/小程序 | ✅​  | ✅​  | ✅​  |
| 抖音    | 链接(分享链接，兼容电脑端链接)    | ✅​  | ✅​  | ❌️  |
| 微博    | 链接(博文，视频，show, 文章)      | ✅​  | ✅​  | ❌️  |
| 小红书  | 链接(含短链)/卡片                 | ✅​  | ✅​  | ❌️  |
| 快手    | 链接(包含标准链接和短链)          | ✅​  | ✅​  | ❌️  |
| acfun   | 链接                              | ✅​  | ❌️  | ❌️  |
| youtube | 链接(含短链)                      | ✅​  | ❌️  | ✅​  |
| tiktok  | 链接                              | ✅​  | ❌️  | ❌️  |
| instagram | 链接                            | ✅​  | ✅​  | ❌️  |
| twitter | 链接                              | ✅​  | ✅​  | ❌️  |

本插件目标：凡是链接皆可解析！尽请期待更新（如果可以,请提交PR）

## 🎨 效果图

插件默认启用 PIL 实现的通用媒体卡片渲染，效果图如下

<div align="center">

<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/video.png" width="160" />
<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/9_pic.png" width="160" />
<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/4_pic.png" width="160" />
<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/repost_video.png" width="160" />
<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/repost_2_pic.png" width="160" />

</div>

## 💿 安装

直接在astrbot的插件市场搜索astrbot_plugin_parser，点击安装，等待完成即可

## ⚙️ 配置

请在astrbot的插件配置面板查看并修改

## 🎉 指令

|   指令   |         权限          |        说明        |
| :------: | :-------------------: |  :---------------: |
| 开启解析 |      ADMIN            |     开启解析      |
| 关闭解析 |      ADMIN            |    关闭解析      |
|    bm    |           -           |  下载 B 站音频   |
|    ym    |           -           |  下载 youtube 音频 |
|  blogin  |      ADMIN           |   扫码获取 B 站凭证 |

## 🧠 插件工作流程

当插件运行后，每一条消息的处理流程如下：

1. **消息接收**  
   监听所有消息事件，获取消息链与原始文本内容  
   - 支持普通文本、链接、卡片（Json 组件）

2. **基础过滤**  
   - 跳过已被禁用的会话  
   - 跳过空消息  
   - 若消息首段为 `@` 且目标不是本 Bot，则不解析

3. **链接提取与匹配**  
   - 若为卡片消息，先从 Json 中提取 URL  
   - 使用「关键词 + 正则」双重匹配，定位对应解析器  
   - 未匹配到解析规则则直接退出

4. **仲裁判定（Emoji Like Arbiter）**  
   - 仅在 `aiocqhttp` 平台生效  
   - 通过固定表情进行 Bot 间仲裁  
   - 未胜出的 Bot 自动放弃解析

5. **防抖判定（Link Debouncer）**  
   - 对同一会话内的相同链接进行时间窗口限制  
   - 命中防抖规则则跳过解析，避免短时间重复处理

6. **解析任务启动**  
   - 创建异步任务执行解析流程  
   - 同一会话仅维护一个运行中的解析任务

7. **内容解析**  
   - 调用对应平台解析器获取媒体信息  
   - 生成统一的 `ParseResult` 数据结构

8. **媒体下载与消息构建**  
   - 下载视频 / 图片 / 音频 / 文件  
   - 根据配置决定音频发送方式  
   - 可按配置提示下载失败项

9. **卡片渲染（可选）**  
   - 在非简洁模式或无直传媒体时生成媒体卡片  
   - 使用 PIL 渲染并缓存图片

10. **消息合并与发送**  
    - 当消息段数量超过阈值时自动合并为转发消息  
    - 最终将结果发送到对应会话

11. **任务回收**  
    - 解析完成或异常后清理任务状态  
    - 插件卸载时统一取消所有运行中的任务

> 整体设计目标：  
> **在保证多 Bot 场景下解析唯一性的前提下，实现稳定、高效、可扩展的链接解析流程。**

## 🧩 扩展

插件支持自定义解析器，通过继承 `BaseParser` 类并实现 `platform`, `handle` 即可。

示例解析器请看 [示例解析器](https://github.com/Zhalslar/astrbot_plugin_parser/blob/main/core/parsers/example.py)

## 🎉 致谢

本项目核心代码来自[nonebot-plugin-parser](https://github.com/fllesser/nonebot-plugin-parser)，请前往原仓库给作者点个Star!

## 变更记录（2026-02-21）
- 修复插件加载失败问题：将 `core/resources/media_button.png` 重新保存为 RGBA（修复 PIL 透明通道断言错误）。
