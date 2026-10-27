import tempfile
import unittest
import zipfile
from pathlib import Path
from content_index import ContentIndex

class ContentTests(unittest.TestCase):
    def test_index_search_refresh_and_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'docs'; root.mkdir()
            other=Path(tmp)/'other'; other.mkdir()
            (root/'notes.txt').write_text('Hello 中华人民共和国 特别任务 Project ZETA',encoding='utf8')
            (root/'password.txt').write_text('hiddenpassword')
            (root/'.hidden.txt').write_text('hiddentext')
            (root/'link.txt').symlink_to(root/'notes.txt')
            with zipfile.ZipFile(root/'word.docx','w') as archive:
                archive.writestr('word/document.xml','<w:document xmlns:w="urn:test"><w:t>UniqueDocumentText</w:t></w:document>')
            idx=ContentIndex(Path(tmp)/'index.sqlite')
            count,errors=idx.scan([str(root)])
            self.assertEqual((count,errors),(2,[]))
            for term in ['中华','共和国','hello zeta','uniquedocument','PROJECT']:
                self.assertEqual(len(idx.search(term,[str(root)])),1,term)
            self.assertIn('Project ZETA',idx.search('project',[str(root)])[0][1])
            self.assertEqual(idx.search('hello',[str(other)]),[])
            self.assertEqual(idx.search('hello',[]),[])
            self.assertEqual(idx.search('hiddenpassword',[str(root)]),[])
            (root/'notes.txt').write_text('changed 新内容',encoding='utf8')
            (root/'word.docx').unlink()
            idx.scan([str(root)])
            self.assertEqual(idx.search('hello',[str(root)]),[])
            self.assertEqual(len(idx.search('新内容',[str(root)])),1)
            self.assertEqual(idx.count(),1)
            count,errors=idx.scan([str(root/'missing')])
            self.assertTrue(errors)
            self.assertEqual(count,1)

    def test_word_format_runs_and_reindex_existing_documents(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'docs'; root.mkdir()
            doc=root/'formatted.docx'
            with zipfile.ZipFile(doc,'w') as archive:
                archive.writestr('word/document.xml', '<w:document xmlns:w="urn:test"><w:p><w:r><w:t>Cross</w:t></w:r><w:r><w:t>Format</w:t></w:r></w:p><w:p><w:t>Second paragraph</w:t></w:p></w:document>')
            database=Path(tmp)/'content.sqlite'
            idx=ContentIndex(database)
            idx.scan([str(root)])
            self.assertEqual(len(idx.search('CrossFormat',[str(root)])),1)
            with sqlite3.connect(database) as db:
                db.execute("UPDATE documents SET text='Cross Format', fold='cross format'")
                db.execute('PRAGMA user_version=0')
            idx=ContentIndex(database)
            idx.scan([str(root)])
            self.assertEqual(len(idx.search('CrossFormat',[str(root)])),1)

    def test_pdf_extract(self):
        import shutil
        if not shutil.which('pdftotext'):
            self.skipTest('pdftotext unavailable')
        import cairo
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'docs'; root.mkdir()
            surface = cairo.PDFSurface(str(root/'sample.pdf'), 400, 300)
            cr = cairo.Context(surface)
            cr.select_font_face('Sans')
            cr.set_font_size(20)
            cr.move_to(30, 50)
            cr.show_text('Unique PDF needle')
            surface.finish()
            idx = ContentIndex(Path(tmp)/'index.sqlite')
            count, errors = idx.scan([str(root)])
            self.assertEqual((count, errors), (1, []))
            self.assertEqual(len(idx.search('pdf needle', [str(root)])), 1)

if __name__=='__main__': unittest.main()
