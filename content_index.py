"""Opt-in local document keyword index, with bounded extraction and incremental updates."""
import os
import select
import shutil
import sqlite3
import subprocess
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from engine import SKIP

EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.pdf', '.docx'}
MAX_SIZE = 8 * 1024 * 1024
MAX_TEXT = 200_000
MAX_XML = 8 * 1024 * 1024
SENSITIVE = ('password', 'passwd', 'secret', 'credential', 'private_key', 'id_rsa', 'id_ed25519', 'token')


def extract(path):
    ext = Path(path).suffix.lower()
    if ext in ('.txt', '.md', '.markdown', '.rst'):
        with open(path, 'rb') as f:
            raw = f.read(MAX_TEXT * 4 + 1)
        if b'\0' in raw:
            return ''
        return raw.decode('utf-8', errors='replace')[:MAX_TEXT]
    if ext == '.pdf':
        if not shutil.which('pdftotext'):
            raise RuntimeError('缺少 pdftotext（请安装 poppler-utils）')
        # Bound output and runtime even for a small but highly compressed PDF.
        proc = subprocess.Popen(['pdftotext','-f','1','-l','30','-enc','UTF-8','-nopgbrk',path,'-'],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        chunks = []
        total = 0
        deadline = time.monotonic() + 15
        try:
            while total < MAX_TEXT * 4:
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise subprocess.TimeoutExpired('pdftotext', 15)
                ready, _, _ = select.select([proc.stdout], [], [], remaining)
                if not ready: raise subprocess.TimeoutExpired('pdftotext', 15)
                chunk = os.read(proc.stdout.fileno(), min(65536, MAX_TEXT * 4-total))
                if not chunk: break
                chunks.append(chunk)
                total += len(chunk)
            if total >= MAX_TEXT * 4:
                proc.kill()
            else:
                proc.wait(timeout=max(0.1, deadline-time.monotonic()))
                if proc.returncode:
                    raise subprocess.CalledProcessError(proc.returncode, 'pdftotext')
            return b''.join(chunks).decode('utf-8',errors='replace')[:MAX_TEXT]
        finally:
            if proc.poll() is None: proc.kill()
            proc.wait()
            proc.stdout.close()
    if ext == '.docx':
        with zipfile.ZipFile(path) as archive:
            member = archive.getinfo('word/document.xml')
            if member.file_size > MAX_XML:
                raise ValueError('document XML too large')
            xml = archive.read(member)
        root = ElementTree.fromstring(xml)
        paragraphs = []
        for paragraph in root.iter():
            if not paragraph.tag.endswith('}p'):
                continue
            pieces = []
            for node in paragraph.iter():
                if node.tag.endswith('}t') and node.text:
                    pieces.append(node.text)
                elif node.tag.endswith('}tab'):
                    pieces.append('\t')
                elif node.tag.endswith('}br') or node.tag.endswith('}cr'):
                    pieces.append('\n')
            paragraphs.append(''.join(pieces))
        # Some minimal DOCX producers omit paragraph wrappers.
        if not paragraphs:
            paragraphs = [''.join(n.text for n in root.iter() if n.tag.endswith('}t') and n.text)]
        return '\n'.join(paragraphs)[:MAX_TEXT]
    return ''


class ContentIndex:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,path TEXT UNIQUE,mtime INTEGER,size INTEGER,text TEXT,fold TEXT,seen INTEGER)')
            db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS document_search USING fts5(fold,content='documents',content_rowid='id',tokenize='trigram')")
            if db.execute('PRAGMA user_version').fetchone()[0] < 1:
                # Re-extract existing DOCX files with the corrected run handling.
                db.execute("UPDATE documents SET mtime=NULL WHERE lower(path) LIKE '%.docx'")
                db.execute('PRAGMA user_version=1')
            db.executescript('''
            CREATE TRIGGER IF NOT EXISTS docs_insert AFTER INSERT ON documents BEGIN INSERT INTO document_search(rowid,fold) VALUES(new.id,new.fold); END;
            CREATE TRIGGER IF NOT EXISTS docs_delete AFTER DELETE ON documents BEGIN INSERT INTO document_search(document_search,rowid,fold) VALUES('delete',old.id,old.fold); END;
            CREATE TRIGGER IF NOT EXISTS docs_update AFTER UPDATE OF fold ON documents BEGIN
              INSERT INTO document_search(document_search,rowid,fold) VALUES('delete',old.id,old.fold);
              INSERT INTO document_search(rowid,fold) VALUES(new.id,new.fold);
            END;''')
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute('PRAGMA cache_size=-4096')
        return db
    def count(self):
        with self.connect() as db:
            return db.execute('SELECT count(*) FROM documents').fetchone()[0]
    def scan(self, roots):
        stamp = time.time_ns()
        errors = []
        missing_pdf = not shutil.which('pdftotext')
        roots = [os.path.abspath(os.path.expanduser(p)) for p in roots]
        if not roots:
            return self.count(), ['请先选择内容搜索目录']
        with self.connect() as db:
            for root in roots:
                if not os.path.isdir(root) or not os.access(root, os.R_OK | os.X_OK):
                    errors.append('目录不可读取：'+root)
                    continue
                def walk_error(exc):
                    errors.append('部分目录不可读取：'+str(exc))
                for parent, dirs, files in os.walk(root,followlinks=False,onerror=walk_error):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in SKIP and not os.path.islink(os.path.join(parent,d))]
                    for name in files:
                        if name.startswith('.') or any(word in name.casefold() for word in SENSITIVE):
                            continue
                        path = os.path.join(parent,name)
                        ext = Path(name).suffix.lower()
                        if ext not in EXTENSIONS or os.path.islink(path): continue
                        try:
                            st = os.stat(path)
                            if not os.path.isfile(path) or st.st_size > MAX_SIZE: continue
                            old = db.execute('SELECT mtime,size FROM documents WHERE path=?',(path,)).fetchone()
                            if old and old == (st.st_mtime_ns,st.st_size):
                                db.execute('UPDATE documents SET seen=? WHERE path=?',(stamp,path))
                            else:
                                if ext == '.pdf' and missing_pdf:
                                    errors.append('缺少 pdftotext；PDF 暂未索引')
                                    continue
                                text = extract(path)
                                db.execute('INSERT INTO documents(path,mtime,size,text,fold,seen) VALUES(?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET mtime=excluded.mtime,size=excluded.size,text=excluded.text,fold=excluded.fold,seen=excluded.seen',
                                           (path,st.st_mtime_ns,st.st_size,text,text.casefold(),stamp))
                            db.commit()
                        except (OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile, ElementTree.ParseError, subprocess.SubprocessError) as exc:
                            db.execute('DELETE FROM documents WHERE path=?', (path,))
                            db.commit()
                            errors.append('部分文档未能读取：'+str(exc))
            # Never erase existing results after an incomplete scan.
            if not errors:
                db.execute('DELETE FROM documents WHERE seen<>?',(stamp,))
                db.commit()
        return self.count(), list(dict.fromkeys(errors))
    def search(self, query, roots, limit=40):
        words = query.casefold().strip().split()
        roots = [os.path.abspath(os.path.expanduser(p)) for p in roots]
        if not words or not roots: return []
        with self.connect() as db:
            terms = [w for w in words if len(w)>=3]
            args = []
            source = 'documents'
            where = []
            if terms:
                source = 'document_search JOIN documents ON documents.id=document_search.rowid'
                where.append('document_search MATCH ?')
                args.append(' AND '.join('"'+w.replace('"','""')+'"' for w in terms))
            where.append('('+' OR '.join('(documents.path=? OR substr(documents.path,1,?)=?)' for _ in roots)+')')
            for root in roots:
                prefix = root.rstrip(os.sep)+os.sep
                args.extend((root, len(prefix), prefix))
            for word in words:
                where.append('instr(documents.fold,?)>0')
                args.append(word)
            sql = 'SELECT documents.path, documents.text FROM '+source+' WHERE '+' AND '.join(where)+' LIMIT ?'
            args.append(limit)
            rows = db.execute(sql,args).fetchall()
        results = []
        for path, text in rows:
            pos = text.casefold().find(words[0])
            start = max(0,pos-20)
            snippet = ' '.join(text[start:pos+len(words[0])+100].split())
            if start: snippet = '…'+snippet
            if pos+len(words[0])+100 < len(text): snippet += '…'
            results.append((path,snippet))
        return results
