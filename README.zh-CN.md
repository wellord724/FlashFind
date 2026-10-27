<div align="center">
  <img src="assets/icon.svg" alt="FlashFind 闪寻图标" width="160" height="160">
  <h1>FlashFind <sub>闪寻</sub></h1>
  <p><strong>所需一切，指尖即达。</strong></p>
  <p>面向 Linux 的本地桌面搜索与应用启动器。</p>
  <p>
    <a href="README.md">English</a> ·
    <a href="README.zh-CN.md">简体中文</a> ·
    <a href="https://github.com/wellord724/FlashFind/releases">下载</a> ·
    <a href="#快速开始">快速开始</a> ·
    <a href="#当前限制">当前限制</a>
  </p>
  <p>
    <img alt="平台：Linux" src="https://img.shields.io/badge/platform-Linux-354c75?style=flat-square">
    <img alt="界面：GTK 3" src="https://img.shields.io/badge/interface-GTK%203-354c75?style=flat-square">
    <img alt="许可证：MIT" src="https://img.shields.io/badge/license-MIT-354c75?style=flat-square">
    <img alt="状态：早期版本" src="https://img.shields.io/badge/status-early%20release-d49e34?style=flat-square">
  </p>
</div>

---

闪寻将应用、文件名和文档文字放在同一个紧凑搜索框中。X11 桌面下连按两下 **Ctrl** 即可唤起，输入关键词后用键盘打开结果。索引留在本机，无需账户、云服务或下载 AI 模型。

> **早期版本：**应用界面目前为中文。已在 Ubuntu 24.04 的 X11 桌面测试，其他发行版和桌面环境可能有差异。

## 功能

- **一个搜索框：**同时搜索已安装应用、文件、文件夹和文档文字。
- **键盘优先：**X11 下双击 Ctrl 唤起，方向键选择，回车打开。
- **本地文档搜索：**支持 UTF-8 TXT、Markdown、RST、DOCX 和有文字层的 PDF，支持中文关键词，并显示命中片段。
- **可选搜索范围：**自行选择要索引内容的目录；文件名默认索引主目录。
- **可调透明背景：**调整背景透明度，文字和图标保持清晰。
- **轻量分发：**使用系统 Python、GTK 3 和 SQLite，无 Electron 或大型模型运行时。

## 快速开始

### Ubuntu / Debian 安装包

从 [Releases](https://github.com/wellord724/FlashFind/releases) 下载 `flashfind_0.1.0_all.deb`，然后执行：

```bash
sudo apt install ./flashfind_0.1.0_all.deb
flashfind
```

`.deb` 是安装包，**不是包含所有依赖的独立二进制文件**；APT 会安装所需系统依赖。已在 Ubuntu 24.04 测试；兼容的 Debian 系系统需要 Python 3、GTK 3、支持 FTS5 trigram 的 SQLite，以及 X11 或 Wayland 桌面。PDF 文字提取使用 `poppler-utils` 中的 `pdftotext`。

### 从源码运行

Ubuntu / Debian：

```bash
sudo apt install python3 python3-gi python3-cairo python3-gi-cairo gir1.2-gtk-3.0 libx11-6 poppler-utils
git clone https://github.com/wellord724/FlashFind.git
cd FlashFind
./start.sh
```

运行 `/usr/bin/python3 install.py` 可添加应用菜单入口，附加 `--autostart` 可选择登录后后台启动。注册后请保留源码目录的位置。

## 使用

1. 启动闪寻，在 X11 下连按两次 **Ctrl** 显示或隐藏搜索框。
2. 输入应用名、文件名或文档里的文字；用 ↑ / ↓ 选择，按 **Enter** 打开。
3. 搜索文档内容前，点击 **选择内容目录**，选择一个或多个文件夹。首次扫描在后台运行，已完成索引的文档会陆续可搜索。
4. 点击 **仅搜索内容** 可以只看文档内容匹配；关闭后同时搜索应用、名称和内容。点击 **透明度** 可调整背景。

| 快捷键 | 功能 |
| --- | --- |
| 连按两次 Ctrl | X11 下显示 / 隐藏 |
| ↑ / ↓ | 选择结果 |
| Enter | 打开结果 |
| Ctrl + Enter | 打开所在文件夹 |
| Esc | 隐藏窗口 |

**Wayland** 下请在系统键盘设置中绑定快捷键到 `flashfind` 命令（源码运行时绑定 `start.sh` 的绝对路径）；双击 Ctrl 仅在 X11 下可用。透明背景需要桌面合成器支持；当前效果不模糊后方窗口。

## 配置与隐私

可选配置文件为 `~/.config/flashfind/config.json`：

```json
{
  "roots": ["~/Documents", "~/Downloads"],
  "content_roots": ["~/Documents"],
  "refresh_seconds": 600,
  "background_transparency": 25
}
```

`roots` 控制文件名索引，`content_roots` 控制文档内容索引。选择或配置目录之前，不会索引文档内容。索引位于本机 `~/.cache/flashfind/`；内容索引包含提取出的文档文字，可供当前用户读取，请根据目录中的文件选择搜索范围。闪寻不会上传这些内容。

启动时和定期（默认每 10 分钟）在后台更新索引，也可点击 **刷新索引**。隐藏文件和目录、符号链接、常见依赖目录以及文件名中包含某些凭据相关词语的文件会被跳过。这些规则不能保证排除所有敏感文字。

## 当前限制

- 使用精确关键词匹配，不是语义搜索；不支持 OCR 或图片、音频、视频内容理解。
- 跳过大于 8 MiB 的文档；单个文档最多索引前 20 万字符，PDF 最多索引前 30 页；扫描版 PDF 无法搜索。
- 文件变化后需要等待下次索引更新；最多显示 40 条结果。
- 透明界面没有背景模糊。快捷键和透明效果取决于桌面会话。
- 资源占用会随文件、索引和桌面环境变化；轻量分发和依赖设计不代表内存占用恒定或最低。

## 开发

```bash
/usr/bin/python3 -m unittest discover -s . -v
./packaging/build-deb.sh
```

打包需要 `dpkg-deb`。安装包的启动命令为 `flashfind`，可使用 `--hidden` 后台启动或 `--quit` 退出运行中的实例。

## 参与贡献

欢迎提交问题和改进。请提供发行版、桌面会话（X11 或 Wayland）、复现步骤和相关错误信息；分享日志或截图前，请移除私人文件名、文档内容和个人信息。

## 许可证

[MIT](LICENSE)。闪寻是独立项目，文档关键词搜索受 [DigUp](https://github.com/ARahim3/DigUp) 等项目启发。
