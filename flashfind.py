#!/usr/bin/python3
import argparse
import ctypes
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from engine import Index, DoubleTap
from content_index import ContentIndex
from search_results import merge_results
from applications import get_applications, search_applications

BASE = Path(os.environ.get('XDG_CACHE_HOME', Path.home()/'.cache'))/'flashfind'
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'flashfind'/'config.json'

def main():
    parser = argparse.ArgumentParser(description='FlashFind · 双击 Ctrl 搜索文件')
    parser.add_argument('--hidden', action='store_true')
    parser.add_argument('--quit', action='store_true')
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    lock = open(BASE/'instance.lock','a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.seek(0)
        os.kill(int(lock.read()), signal.SIGTERM if args.quit else signal.SIGUSR1)
        return
    if args.quit:
        return
    lock.seek(0); lock.truncate(); lock.write(str(os.getpid())); lock.flush()
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk, Gdk, GLib, Gio, Pango
    config = {'roots':[str(Path.home())], 'refresh_seconds':600, 'background_transparency':25, 'content_roots':[]}
    if CONFIG.exists():
        config.update(json.loads(CONFIG.read_text()))
    index = Index(BASE/'index.sqlite3')
    content_index = ContentIndex(BASE/'content.sqlite3')
    pool = ThreadPoolExecutor(max_workers=1)
    css = Gtk.CssProvider()
    css.load_from_data(b'''
    .flash-window {color:#f4f7ff; border-radius:18px;}
    entry {background:#222835;color:#f5f7fb;border:1px solid #39465c;border-radius:12px;padding:13px;font-size:21px;caret-color:#7da9ff;}
    list {background:transparent;} row label {color:#f7f9ff;} row label.muted {color:#c3d0e5;} row {border-radius:10px;padding:7px;background:rgba(15,22,35,0.82);} row:selected {background:#304b76;}
    .muted {color:#c5d4ea;font-size:12px;} .brand {color:#d1e1ff;font-size:12px;font-weight:bold;} .glass-caption {background:rgba(15,22,35,0.78);border-radius:6px;padding:3px 7px;}
    button {background:#262f3d;color:#dbe5f5;border:0;box-shadow:none;} button:checked {background:#41699f;color:#fff;} popover .muted {color:#56677d;}
    ''')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    win = Gtk.Window(title='FlashFind · 闪寻')
    win.get_style_context().add_class('flash-window')
    screen = win.get_screen()
    rgba = screen.get_rgba_visual()
    glass_supported = bool(rgba and screen.is_composited())
    if rgba:
        win.set_visual(rgba)
    win.set_app_paintable(True)
    glass_css = Gtk.CssProvider()
    win.get_style_context().add_provider(glass_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
    def paint_background(widget, cr):
        # Clear the window first so transparent corners and the alpha channel are
        # composed correctly by the desktop compositor.
        import cairo
        cr.save()
        cr.set_operator(cairo.OPERATOR_SOURCE)
        Gtk.render_background(widget.get_style_context(), cr, 0, 0,
                              widget.get_allocated_width(), widget.get_allocated_height())
        cr.restore()
        return False
    win.connect('draw', paint_background)
    try:
        transparency = max(0, min(70, int(config.get('background_transparency', 25))))
    except (TypeError, ValueError):
        transparency = 25
    def apply_transparency(value):
        alpha = 1 - value / 100 if glass_supported else 1
        glass_css.load_from_data(('.flash-window { background-color: rgba(23, 29, 43, %.2f); '
                                  'border: 1px solid rgba(213, 226, 255, 0.27); '
                                  'border-radius: 18px; }' % alpha).encode())
        win.queue_draw()
    apply_transparency(transparency)
    win.set_icon_from_file(str(Path(__file__).resolve().parent/'flashfind.svg'))
    win.set_default_size(700,520)
    win.set_resizable(False)
    win.set_decorated(False)
    win.set_keep_above(True)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.set_border_width(20)
    win.connect('delete-event', lambda *_: (win.hide() or True))
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
    win.add(outer)
    header = Gtk.Box(spacing=12)
    brand = Gtk.Label(label='⚡  FLASHFIND  /  闪寻',xalign=0)
    brand.get_style_context().add_class('brand')
    brand.get_style_context().add_class('glass-caption')
    header.pack_start(brand,True,True,0)
    glass_button = Gtk.MenuButton(label='透明度')
    glass_button.set_tooltip_text('调整搜索框的背景透明度')
    glass_popover = Gtk.Popover.new(glass_button)
    glass_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    glass_box.set_border_width(14)
    glass_label = Gtk.Label(xalign=0)
    glass_box.pack_start(glass_label, False, False, 0)
    glass_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 70, 5)
    glass_scale.set_size_request(190, -1)
    glass_scale.set_draw_value(False)
    glass_scale.set_value(transparency)
    glass_box.pack_start(glass_scale, False, False, 0)
    glass_hint = Gtk.Label(label=('仅调整背景，文字保持清晰' if glass_supported else '桌面未开启合成，背景保持不透明'), xalign=0)
    glass_hint.get_style_context().add_class('muted')
    glass_box.pack_start(glass_hint, False, False, 0)
    glass_popover.add(glass_box)
    glass_box.show_all()
    glass_button.set_popover(glass_popover)
    header.pack_start(glass_button,False,False,0)
    save_timer = [None]
    def persist_transparency():
        save_timer[0] = None
        try:
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            existing = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
            existing['background_transparency'] = int(glass_scale.get_value())
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=CONFIG.parent,
                                             prefix='.config-', delete=False) as tmp:
                try:
                    json.dump(existing, tmp, ensure_ascii=False, indent=2)
                    tmp.write('\n')
                    tmp.flush()
                    os.replace(tmp.name, CONFIG)
                finally:
                    if os.path.exists(tmp.name):
                        os.unlink(tmp.name)
        except (OSError, ValueError) as exc:
            status.set_text('无法保存透明度：' + str(exc))
        return False
    def transparency_changed(scale):
        value = int(scale.get_value())
        glass_label.set_text(f'背景透明度  {value}%')
        apply_transparency(value)
        if save_timer[0]:
            GLib.source_remove(save_timer[0])
        save_timer[0] = GLib.timeout_add(350, persist_transparency)
    glass_label.set_text(f'背景透明度  {transparency}%')
    glass_scale.connect('value-changed', transparency_changed)
    refresh = Gtk.Button(label='刷新索引')
    header.pack_start(refresh,False,False,0)
    close = Gtk.Button(label='隐藏  Esc')
    close.connect('clicked',lambda *_: win.hide())
    header.pack_start(close,False,False,0)
    outer.pack_start(header,False,False,0)
    entry = Gtk.Entry()
    entry.set_placeholder_text('搜索应用、文件名或文档内容…')
    outer.pack_start(entry,False,False,0)
    content_bar = Gtk.Box(spacing=8)
    content_toggle = Gtk.ToggleButton(label='仅搜索内容')
    content_toggle.set_tooltip_text('默认同时搜索名称和内容；打开后仅显示文档内容匹配')
    content_bar.pack_start(content_toggle, False, False, 0)
    content_choose = Gtk.Button(label='选择内容目录')
    content_choose.set_tooltip_text('选择需要搜索文件内容的目录')
    content_bar.pack_start(content_choose, False, False, 0)
    content_scope = Gtk.Label(xalign=0)
    content_scope.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
    content_scope.get_style_context().add_class('muted')
    content_scope.get_style_context().add_class('glass-caption')
    content_bar.pack_start(content_scope, True, True, 0)
    outer.pack_start(content_bar,False,False,0)
    status = Gtk.Label(xalign=0)
    status.get_style_context().add_class('muted')
    status.get_style_context().add_class('glass-caption')
    outer.pack_start(status,False,False,0)
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
    scroll.set_min_content_height(310)
    results = Gtk.ListBox()
    results.set_selection_mode(Gtk.SelectionMode.SINGLE)
    scroll.add(results)
    outer.pack_start(scroll,True,True,0)
    footer = Gtk.Label(label='Ctrl × 2 唤起    ↑↓ 选择    Enter 打开    Ctrl+Enter 所在目录',xalign=0)
    footer.get_style_context().add_class('muted')
    footer.get_style_context().add_class('glass-caption')
    outer.pack_start(footer,False,False,0)
    state = {'generation':0,'timer':None,'busy':False,'count':index.count(),'future':None,
             'content_busy':False,'content_count':content_index.count(),'content_version':0}
    apps = get_applications()
    app_monitor = Gio.AppInfoMonitor.get()
    def reload_apps(*_):
        nonlocal apps
        apps = get_applications()
        changed()
    app_monitor.connect('changed', reload_apps)
    def update_content_scope():
        roots = config.get('content_roots', [])
        content_scope.set_text('内容范围：' + ('、'.join(roots) if roots else '未选择'))
        content_scope.set_tooltip_text('内容范围：' + ('\n'.join(roots) if roots else '未选择'))
    update_content_scope()
    def idle_status():
        if content_toggle.get_active():
            if not config.get('content_roots'):
                status.set_text('请点击“选择内容目录”，选择要搜索的文件夹')
            else:
                status.set_text(f"内容索引：{state['content_count']:,} 个文档" + (' · 正在后台更新' if state['content_busy'] else ' · 输入文档中的词语'))
            return
        status.set_text(f"文件 {state['count']:,} 项 · 文档 {state['content_count']:,} 个 · 搜索名称与内容" + (' · 后台更新中' if state['busy'] or state['content_busy'] else ''))
    def display(rows, elapsed, generation, error=None):
        if generation != state['generation']:
            return False
        for child in results.get_children():
            results.remove(child)
        for result in rows:
            row = Gtk.ListBoxRow()
            row.app = result.get('app')
            row.path = result.get('path')
            name = result['name']
            box = Gtk.Box(spacing=12)
            if row.app:
                gicon = row.app.get_icon() or Gio.ThemedIcon.new('application-x-executable')
                detail = '应用程序 · ' + (row.app.get_description() or row.app.get_id() or '')
            else:
                detail = row.path
                if result['kind']:
                    gicon = Gio.ThemedIcon.new('folder')
                else:
                    content_type, _ = Gio.content_type_guess(row.path, None)
                    gicon = Gio.content_type_get_icon(content_type) if content_type else Gio.ThemedIcon.new('text-x-generic')
            icon = Gtk.Image.new_from_gicon(gicon, Gtk.IconSize.DIALOG)
            icon.set_pixel_size(40)
            box.pack_start(icon,False,False,0)
            texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5)
            lines = [(name,False),(detail,True)]
            if result.get('snippet'):
                lines.append(('内容：' + result['snippet'],True))
            for text, muted in lines:
                label = Gtk.Label(label=text,xalign=0)
                label.set_ellipsize(Pango.EllipsizeMode.END if text.startswith('内容：') else Pango.EllipsizeMode.MIDDLE)
                label.set_max_width_chars(72)
                if muted: label.get_style_context().add_class('muted')
                texts.pack_start(label,False,False,0)
            box.pack_start(texts,True,True,0)
            row.add(box); results.add(row)
        results.show_all()
        if rows: results.select_row(results.get_row_at_index(0))
        if error: status.set_text('搜索失败：'+error)
        elif content_toggle.get_active() and not config.get('content_roots'):
            idle_status()
        elif entry.get_text().strip(): status.set_text(f"{len(rows)} 个结果{'（最多显示 40 项）' if len(rows)==40 else ''} · {elapsed:.1f} ms" if rows else '没有匹配结果 · 可刷新索引或调整搜索范围')
        else: idle_status()
        return False
    def query():
        state['timer'] = None
        generation = state['generation']
        text = entry.get_text()
        content_mode = content_toggle.get_active()
        roots = list(config.get('content_roots', []))
        matching_apps = [] if content_mode else search_applications(apps, text)
        if state['future']: state['future'].cancel()
        def work():
            start = time.perf_counter()
            try:
                files = [] if content_mode else index.search(text)
                app_paths = {a.get_filename() for a in matching_apps if isinstance(a, Gio.DesktopAppInfo)}
                rows = [{'name': a.get_display_name(), 'app': a} for a in matching_apps]
                rows.extend({'path': path, 'name': name, 'kind': kind}
                            for path, name, kind in files if path not in app_paths)
                contents = [{'path': path, 'name': Path(path).name, 'kind': 0, 'snippet': snippet}
                            for path, snippet in content_index.search(text, roots)]
                rows = contents if content_mode else merge_results(rows, contents)
                GLib.idle_add(display, rows[:40], (time.perf_counter()-start)*1000, generation)
            except Exception as exc: GLib.idle_add(display,[],0,generation,str(exc))
        state['future'] = pool.submit(work)
        return False
    def changed(*_):
        state['generation'] += 1
        # Never let Enter open a result from an earlier query.
        for row in results.get_children():
            results.remove(row)
        if entry.get_text().strip():
            status.set_text('正在搜索…')
        if state['timer']: GLib.source_remove(state['timer'])
        state['timer'] = GLib.timeout_add(45,query)
    entry.connect('changed',changed)
    def mode_changed(*_):
        entry.set_placeholder_text('搜索文档中的关键词…' if content_toggle.get_active() else '搜索应用、文件名或文档内容…')
        changed()
    content_toggle.connect('toggled', mode_changed)

    def save_content_roots(roots):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
        existing['content_roots'] = roots
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=CONFIG.parent, prefix='.config-', delete=False) as tmp:
            try:
                json.dump(existing, tmp, ensure_ascii=False, indent=2)
                tmp.write('\n'); tmp.flush()
                os.replace(tmp.name, CONFIG)
            finally:
                if os.path.exists(tmp.name): os.unlink(tmp.name)

    def choose_content_roots(*_):
        dialog = Gtk.FileChooserDialog(title='选择要搜索内容的文件夹', transient_for=win,
                                       action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons('取消', Gtk.ResponseType.CANCEL, '选择', Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        dialog.set_current_folder(str(Path.home()))
        response = dialog.run()
        roots = dialog.get_filenames() if response == Gtk.ResponseType.OK else None
        dialog.destroy()
        if roots:
            try:
                save_content_roots(roots)
            except (OSError, ValueError) as exc:
                status.set_text('无法保存目录：' + str(exc)); return
            config['content_roots'] = roots
            state['content_version'] += 1
            update_content_scope()
            changed()
            reindex_content()
    content_choose.connect('clicked',choose_content_roots)

    def content_finished(version, count, errors):
        state['content_busy'] = False
        state['content_count'] = count
        if version != state['content_version']:
            reindex_content()
        elif errors:
            status.set_text('内容索引：' + errors[0])
        else:
            changed()
        return False

    def reindex_content():
        if state['content_busy'] or not config.get('content_roots'):
            return
        state['content_busy'] = True
        version = state['content_version']
        roots = list(config['content_roots'])
        if content_toggle.get_active(): idle_status()
        def work():
            try:
                count, errors = content_index.scan(roots)
                GLib.idle_add(content_finished, version, count, errors)
            except Exception as exc:
                GLib.idle_add(content_finished, version, state['content_count'], [str(exc)])
        threading.Thread(target=work, daemon=True).start()
    def open_result(folder=False):
        row = results.get_selected_row()
        if not row: return
        if row.app and not folder:
            try:
                context = Gdk.Display.get_default().get_app_launch_context()
                if row.app.launch([], context):
                    win.hide()
                else:
                    status.set_text('应用未能启动')
            except GLib.Error as exc:
                status.set_text('无法启动应用：' + exc.message)
            return
        if row.app:
            filename = row.app.get_filename() if isinstance(row.app, Gio.DesktopAppInfo) else None
            if not filename:
                status.set_text('无法找到应用的启动文件'); return
            path = Path(filename).parent
        else:
            path = Path(row.path)
            if folder: path = path.parent
        if not path.exists():
            status.set_text('文件已移动或删除，请刷新索引'); return
        try:
            Gio.AppInfo.launch_default_for_uri(path.as_uri(),None)
            win.hide()
        except GLib.Error as exc: status.set_text('无法打开：'+exc.message)
    results.connect('row-activated',lambda *_: open_result())
    def keypress(_,event):
        if event.keyval == Gdk.KEY_Escape: win.hide(); return True
        if event.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter):
            open_result(bool(event.state & Gdk.ModifierType.CONTROL_MASK)); return True
        if event.keyval in (Gdk.KEY_Down,Gdk.KEY_Up):
            row = results.get_selected_row()
            n = (row.get_index() if row else -1) + (1 if event.keyval==Gdk.KEY_Down else -1)
            n = max(0,min(len(results.get_children())-1,n))
            row = results.get_row_at_index(n)
            if row:
                results.select_row(row)
                allocation = row.get_allocation()
                adjust = scroll.get_vadjustment()
                adjust.clamp_page(allocation.y,allocation.y+allocation.height)
            return True
        return False
    win.connect('key-press-event',keypress)
    def toggle(*_):
        if win.get_visible(): win.hide()
        else:
            win.show_all()
            timestamp = Gdk.CURRENT_TIME
            if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
                gi.require_version('GdkX11','3.0')
                from gi.repository import GdkX11
                timestamp = GdkX11.x11_get_server_time(win.get_window())
            win.present_with_time(timestamp)
            win.get_window().focus(timestamp)
            entry.grab_focus(); entry.select_region(0,-1)
        return True
    def finished(count,error):
        state['busy']=False; state['count']=count
        refresh.set_sensitive(True)
        if error: status.set_text('索引更新失败：'+error)
        else: changed()
        return False
    def reindex(*_):
        reindex_content()
        if state['busy']: return True
        state['busy']=True; refresh.set_sensitive(False); idle_status()
        def work():
            try:
                count=index.scan(config['roots'])
                GLib.idle_add(finished,count,None)
            except Exception as exc: GLib.idle_add(finished,state['count'],str(exc))
        threading.Thread(target=work,daemon=True).start()
        return True
    refresh.connect('clicked',reindex)
    GLib.timeout_add_seconds(max(60,int(config['refresh_seconds'])),reindex)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGUSR1,toggle)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,lambda: (Gtk.main_quit() or False))
    # Poll X11 key states without grabbing keys or interfering with shortcuts.
    if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
        x = ctypes.CDLL('libX11.so.6')
        x.XOpenDisplay.argtypes=[ctypes.c_char_p]; x.XOpenDisplay.restype=ctypes.c_void_p
        x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong]; x.XKeysymToKeycode.restype=ctypes.c_ubyte
        x.XQueryKeymap.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
        display_x = x.XOpenDisplay(None)
        if display_x:
            ctrl_codes={x.XKeysymToKeycode(display_x,0xffe3),x.XKeysymToKeycode(display_x,0xffe4)}
            buf=(ctypes.c_ubyte*32)(); detector=DoubleTap()
            def poll():
                x.XQueryKeymap(display_x,buf)
                keys={i for i in range(8,256) if buf[i//8] & (1 << (i%8))}
                if detector.update(bool(keys & ctrl_codes),bool(keys-ctrl_codes),time.monotonic()): toggle()
                return True
            GLib.timeout_add(20,poll)
    else:
        footer.set_text('Wayland：请在系统设置绑定启动命令    ↑↓ 选择    Enter 打开    Esc 隐藏')
    idle_status()
    reindex()
    if not args.hidden: toggle()
    Gtk.main()
    if save_timer[0]:
        GLib.source_remove(save_timer[0])
        persist_transparency()
    pool.shutdown(wait=False,cancel_futures=True)

if __name__ == '__main__':
    main()
