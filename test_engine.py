import tempfile
import unittest
from pathlib import Path
from engine import Index, DoubleTap

class Tests(unittest.TestCase):
    def test_search_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'files'; root.mkdir()
            for name in ['中文测试.txt','Annual Report.PDF','100%_done.txt','a"quoted.txt']:
                (root/name).touch()
            (root/'.secret').touch()
            (root/'node_modules').mkdir()
            (root/'node_modules'/'ignored').touch()
            idx=Index(Path(tmp)/'db.sqlite')
            self.assertEqual(idx.scan([str(root)]),4)
            for query in ['中文','中文测','REPORT','annual pdf','100%_','a"q']:
                self.assertEqual(len(idx.search(query)),1,query)
            self.assertEqual(idx.search('ignored'),[])
            (root/'中文测试.txt').unlink()
            idx.scan([str(root)])
            self.assertEqual(idx.search('中文'),[])
    def test_unavailable_root_does_not_delete_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'files'; root.mkdir()
            (root/'keep.md').write_text('data')
            idx = Index(Path(tmp)/'db.sqlite')
            idx.scan([str(root)])
            with self.assertRaises(RuntimeError):
                idx.scan([str(root), str(Path(tmp)/'missing')])
            self.assertEqual(len(idx.search('keep')),1)

    def test_hotkey(self):
        tap=DoubleTap()
        self.assertFalse(tap.update(True,False,1))
        self.assertFalse(tap.update(False,False,1.1))
        self.assertFalse(tap.update(True,False,1.2))
        self.assertTrue(tap.update(False,False,1.3))
        tap.update(True,True,2)
        self.assertFalse(tap.update(False,False,2.1))
        tap.update(True,False,2.2)
        self.assertFalse(tap.update(False,False,2.3))
        tap.update(True,False,3)
        self.assertFalse(tap.update(False,False,4))

if __name__=='__main__': unittest.main()
