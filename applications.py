"""Discover launchable desktop applications using the XDG application registry."""
import os
from gi.repository import Gio


def get_applications():
    apps = []
    for app in Gio.AppInfo.get_all():
        if not app.should_show() or not app.get_id():
            continue
        # Names, generic names, keywords, IDs and executable names all help users
        # find an application, regardless of desktop locale.
        fields = [app.get_display_name(), app.get_name(), app.get_id(), os.path.basename(app.get_executable() or "")]
        if isinstance(app, Gio.DesktopAppInfo):
            fields += [app.get_string('Name'), app.get_string('GenericName'), app.get_locale_string('GenericName'), app.get_string('Keywords'), app.get_locale_string('Keywords')]
        haystack = ' '.join(str(v).casefold() for v in fields if v)
        apps.append((app, haystack))
    return apps


def search_applications(apps, query, limit=12):
    words = query.strip().casefold().split()
    if not words:
        return []
    matches = []
    for app, haystack in apps:
        if all(word in haystack for word in words):
            name = app.get_display_name()
            folded = name.casefold()
            rank = (not all(w in folded for w in words), folded != ' '.join(words), not folded.startswith(words[0]), len(name), folded)
            matches.append((rank, app))
    matches.sort(key=lambda item: item[0])
    return [app for _, app in matches[:limit]]
