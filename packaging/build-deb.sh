#!/bin/sh
set -eu
umask 022
project_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
version=0.1.0
out_dir=${1:-"$project_dir/dist"}
mkdir -p "$out_dir"
out_dir=$(CDPATH='' cd -- "$out_dir" && pwd)
stage=$(mktemp -d)
chmod 755 "$stage"
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
mkdir -p "$stage/DEBIAN" "$stage/usr/lib/flashfind" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps" "$stage/usr/share/doc/flashfind"
cat > "$stage/DEBIAN/control" <<CONTROL
Package: flashfind
Version: $version
Section: utils
Priority: optional
Architecture: all
Maintainer: FlashFind contributors
Depends: python3 (>= 3.9), python3-gi, python3-cairo, python3-gi-cairo, gir1.2-gtk-3.0, libx11-6, poppler-utils
Description: fast local application, filename and document search for Linux
 FlashFind is a GTK desktop search utility with keyboard navigation, local
 document keyword indexing and a double-Control shortcut on X11.
CONTROL
for file in applications.py content_index.py engine.py flashfind.py search_results.py flashfind.svg; do
    install -m 644 "$project_dir/$file" "$stage/usr/lib/flashfind/$file"
done
cat > "$stage/usr/bin/flashfind" <<'LAUNCHER'
#!/bin/sh
exec /usr/bin/python3 /usr/lib/flashfind/flashfind.py "$@"
LAUNCHER
chmod 755 "$stage/usr/bin/flashfind"
install -m 644 "$project_dir/packaging/flashfind.desktop" "$stage/usr/share/applications/flashfind.desktop"
install -m 644 "$project_dir/flashfind.svg" "$stage/usr/share/icons/hicolor/scalable/apps/flashfind.svg"
install -m 644 "$project_dir/LICENSE" "$stage/usr/share/doc/flashfind/copyright"
dpkg-deb --root-owner-group --build "$stage" "$out_dir/flashfind_${version}_all.deb"
