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