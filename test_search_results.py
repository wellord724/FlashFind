import unittest
from search_results import merge_results

class MergeTests(unittest.TestCase):
    def test_content_is_visible_when_name_results_are_full(self):
        names = [{'path':str(i),'name':str(i),'kind':0} for i in range(40)]
        contents = [{'path':'target.md','snippet':'本机','name':'target.md','kind':0}]
        results = merge_results(names,contents)
        self.assertEqual(len(results),40)
        self.assertIn('target.md', [r.get('path') for r in results])
    def test_same_file_appears_once_and_has_snippet(self):
        names=[{'path':'test.md','name':'test.md','kind':0}]
        contents=[{'path':'test.md','name':'test.md','kind':0,'snippet':'example'}]
        rows=merge_results(names,contents)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['snippet'],'example')
    def test_name_outside_limit_can_show_as_content(self):
        names=[{'path':str(i),'name':str(i),'kind':0} for i in range(50)]
        contents=[{'path':'49','name':'49','kind':0,'snippet':'found'}]
        rows=merge_results(names,contents)
        self.assertIn('49',[r.get('path') for r in rows])
        self.assertEqual(len(rows),40)

if __name__=='__main__': unittest.main()
