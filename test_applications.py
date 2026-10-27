import unittest
from gi.repository import Gio
from applications import search_applications

class ApplicationSearchTests(unittest.TestCase):
    def test_names_keywords_and_order(self):
        apps = []
        for name, keywords in [('Visual Studio Code', 'editor development'), ('Code Blocks', 'development editor')]:
            info = Gio.AppInfo.create_from_commandline('/bin/true', name, Gio.AppInfoCreateFlags.NONE)
            apps.append((info, (name + ' ' + keywords).casefold()))
        self.assertEqual([a.get_name() for a in search_applications(apps, 'code')], ['Code Blocks', 'Visual Studio Code'])
        self.assertEqual(len(search_applications(apps, 'editor development')), 2)
        self.assertEqual(search_applications(apps, 'missing'), [])
        self.assertEqual(search_applications(apps, ' '), [])

if __name__ == '__main__': unittest.main()
