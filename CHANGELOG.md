# Changelog

## 2026-02-23

### Fixed
- 修复 `core/resources/media_button.png` 在部分环境下导致 Pillow `AssertionError` 进而引发插件加载失败的问题。
- 为 `Renderer._load_video_button` 增加容错：图片资源损坏/解码异常时自动降级为透明占位图，确保插件可继续启动。
- 兼容当前运行环境的 `apilmoji` 版本：移除 `EmojiCDNSource` 不支持的 `enable_tqdm` 参数，避免 `TypeError` 导致插件初始化失败。

### Notes
- 本次修复优先保障“可加载、可运行、可降级”，避免单个资源异常拖垮整个插件。
