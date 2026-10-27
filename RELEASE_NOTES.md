# FlashFind 0.1.0

Early Linux release of FlashFind, a local-first application, filename and document keyword search utility.

- Search installed applications, files and document text from one window.
- Double-tap Ctrl on X11, use keyboard navigation and adjust the transparent background.
- Index selected folders locally; supports UTF-8 TXT, Markdown, RST, DOCX and text-based PDF.
- Includes a Debian/Ubuntu `.deb` installer and source archive. The installer uses system Python and GTK dependencies; it is not a self-contained binary.

The interface is currently in Chinese. Tested on Ubuntu 24.04 / X11. Wayland needs a shortcut configured in the desktop settings. Document search is exact keyword matching, not semantic search or OCR. See the README for file-size limits, privacy details and known limitations.

---

闪寻的早期 Linux 版本，支持本地应用、文件名和文档关键词搜索。X11 下可双击 Ctrl 唤起；Wayland 需在系统设置中配置快捷键。包含 Debian / Ubuntu 安装包和源码压缩包；安装包依赖系统 Python 与 GTK，并非独立二进制。具体支持范围和限制请参阅 README。
