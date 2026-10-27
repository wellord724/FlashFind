<div align="center">
  <img src="assets/icon.svg" alt="FlashFind logo" width="160" height="160">
  <h1>FlashFind <sub>闪寻</sub></h1>
  <p><strong>Find what you need, right from your keyboard.</strong></p>
  <p>A local-first desktop search and application launcher for Linux.</p>
  <p>
    <a href="README.md">English</a> ·
    <a href="README.zh-CN.md">简体中文</a> ·
    <a href="https://github.com/wellord724/FlashFind/releases">Downloads</a> ·
    <a href="#getting-started">Getting started</a> ·
    <a href="#limitations">Limitations</a>
  </p>
  <p>
    <img alt="Platform: Linux" src="https://img.shields.io/badge/platform-Linux-354c75?style=flat-square">
    <img alt="Interface: GTK 3" src="https://img.shields.io/badge/interface-GTK%203-354c75?style=flat-square">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-354c75?style=flat-square">
    <img alt="Status: early release" src="https://img.shields.io/badge/status-early%20release-d49e34?style=flat-square">
  </p>
</div>

---

FlashFind brings applications, filenames and document text into one compact search window. Double-tap **Ctrl** on X11, type a few words and open a result without leaving the keyboard. The index stays on your machine; there is no account, cloud service or AI model to download.

> **Early release:** The application interface is currently in Chinese. The project has been tested on Ubuntu 24.04 with X11; other distributions and desktop environments may behave differently.

## Highlights

- **One search box** for installed applications, files, folders and document text.
- **Keyboard-first:** double-tap Ctrl on X11, use arrow keys and press Enter.
- **Local document search:** matches text in UTF-8 TXT, Markdown, RST, DOCX and text-based PDF files, including Chinese keywords. Results include a matching excerpt.
- **Configurable scope:** choose which folders are indexed for document content. Filename indexing defaults to your home directory.
- **Transparent background:** adjust the background opacity while keeping labels and icons readable.
- **Small application package:** uses Python, GTK 3 and SQLite supplied by your system; no Electron or large model runtime.

## Getting started

### Ubuntu / Debian package

Download `flashfind_0.1.0_all.deb` from [Releases](https://github.com/wellord724/FlashFind/releases), then install it:

```bash
sudo apt install ./flashfind_0.1.0_all.deb
flashfind
```

The `.deb` is an installer, **not a self-contained binary**. APT installs its system dependencies. It has been tested on Ubuntu 24.04; compatible Debian-based systems require Python 3, GTK 3, SQLite with the FTS5 trigram tokenizer, and an X11 or Wayland desktop. PDF text extraction uses `pdftotext` from `poppler-utils`.

### Run from source

On Ubuntu / Debian:

```bash
sudo apt install python3 python3-gi python3-cairo python3-gi-cairo gir1.2-gtk-3.0 libx11-6 poppler-utils
git clone https://github.com/wellord724/FlashFind.git
cd FlashFind
./start.sh
```

For a menu entry, run `/usr/bin/python3 install.py`. Add `--autostart` to opt in to starting in the background at login. The source directory must remain in place after registration.

## How to use

1. Start FlashFind. On X11, press **Ctrl twice** to show or hide it.
2. Enter a name or words found inside a document. Use ↑ / ↓ to select and **Enter** to open.
3. For document contents, click **选择内容目录** and choose one or more folders. The first scan runs in the background. Search results can appear as documents are indexed.
4. Click **仅搜索内容** to show only content matches, or leave it off to search applications, names and content together. Use **透明度** to adjust the background.

| Shortcut | Action |
| --- | --- |
| Ctrl twice | Show / hide on X11 |
| ↑ / ↓ | Select a result |
| Enter | Open the result |
| Ctrl + Enter | Open its containing folder |
| Esc | Hide the window |

On **Wayland**, bind a system keyboard shortcut to the `flashfind` command (or the absolute path to `start.sh` for a source checkout). Double-tap Ctrl is available on X11 only. Background transparency requires a compositor; the current effect does not blur windows behind it.

## Configuration and privacy

The optional configuration file is `~/.config/flashfind/config.json`:

```json
{
  "roots": ["~/Documents", "~/Downloads"],
  "content_roots": ["~/Documents"],
  "refresh_seconds": 600,
  "background_transparency": 25
}
```

`roots` controls filename indexing; `content_roots` controls document text indexing. Document content is not indexed until a folder is selected or configured. Indexes are stored locally in `~/.cache/flashfind/`; the content index contains extracted document text and is accessible to the current user. Consider what is in a folder before indexing it. Nothing is uploaded by FlashFind.

Indexes update in the background at startup and periodically (10 minutes by default), or when you click **刷新索引**. Hidden files and directories, symlinks, common dependency directories and filenames containing certain credential-related terms are skipped. These heuristics are not a guarantee that sensitive text will be excluded.

## Limitations

- Exact keyword search, not semantic search, OCR, or image / audio / video understanding.
- Document files over 8 MiB are skipped; at most 200,000 characters per document and the first 30 PDF pages are indexed. PDF scans without a text layer cannot be searched.
- Files change on disk between scans; the index may be stale until the next refresh. At most 40 results are displayed.
- The transparent interface has no backdrop blur. Shortcut support and compositor behavior depend on the desktop session.
- Resource usage depends on your files, index and desktop environment. The application is lightweight in distribution and dependency design, but memory usage is not guaranteed to be minimal.

## Development

```bash
/usr/bin/python3 -m unittest discover -s . -v
./packaging/build-deb.sh
```

The package script requires `dpkg-deb`. The `.deb` launch command is `flashfind`; pass `--hidden` for a background start or `--quit` to stop the running instance.

## Contributing

Bug reports and pull requests are welcome. Include your distribution, desktop session (X11 or Wayland), steps to reproduce and relevant error messages. Please remove private filenames, document contents and personal information from logs and screenshots before sharing them.

## License

[MIT](LICENSE). FlashFind is an independent project; document keyword search was inspired by projects such as [DigUp](https://github.com/ARahim3/DigUp).
