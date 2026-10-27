"""Local filename index; GTK-free so it can be tested independently."""
import os
import sqlite3
import time
from pathlib import Path

SKIP = {'node_modules', '__pycache__', 'venv', 'env', 'anaconda3', 'miniconda3', 'site-packages', 'proc', 'sys', 'dev'}

class Index:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY,path TEXT UNIQUE,name TEXT,fold TEXT,kind INTEGER,seen INTEGER)')
            db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS names USING fts5(fold,content='files',content_rowid='id',tokenize='trigram')")
            db.executescript('''
            CREATE TRIGGER IF NOT EXISTS ai AFTER INSERT ON files BEGIN INSERT INTO names(rowid,fold) VALUES(new.id,new.fold); END;
            CREATE TRIGGER IF NOT EXISTS ad AFTER DELETE ON files BEGIN INSERT INTO names(names,rowid,fold) VALUES('delete',old.id,old.fold); END;
            ''')
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute('PRAGMA cache_size=-4096')
        return db
    def scan(self, roots, progress=lambda n: None):
        stamp = time.time_ns()
        batch = []
        count = 0
        errors = []
        with self.connect() as db:
            def flush():
                nonlocal count
                db.executemany('INSERT INTO files(path,name,fold,kind,seen) VALUES(?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET seen=excluded.seen,kind=excluded.kind', batch)
                db.commit()
                count += len(batch)
                batch.clear()
                progress(count)
            for root in roots:
                root = os.path.abspath(os.path.expanduser(root))
                if not os.path.isdir(root) or not os.access(root, os.R_OK | os.X_OK):
                    errors.append('目录不可读取：' + root)
                    continue
                def walk_error(exc):
                    errors.append('部分目录不可读取：' + str(exc))
                for parent, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in SKIP]
                    for name in dirs + files:
                        if name.startswith('.'):
                            continue
                        path = os.path.join(parent, name)
                        batch.append((path,name,name.casefold(),int(name in dirs),stamp))
                        if len(batch) >= 1000:
                            flush()
            flush()
            if not errors and roots:
                db.execute('DELETE FROM files WHERE seen<>?', (stamp,))
        if errors:
            raise RuntimeError(errors[0])
        return count
    def count(self):
        with self.connect() as db:
            return db.execute('SELECT count(*) FROM files').fetchone()[0]
    def search(self, query, limit=40):
        tokens = query.strip().casefold().split()
        with self.connect() as db:
            if not tokens:
                return []
            terms = [t for t in tokens if len(t) >= 3]
            args = []
            source = 'files'
            conditions = []
            if terms:
                source = 'names JOIN files ON files.id=names.rowid'
                conditions.append('names MATCH ?')
                args.append(' AND '.join('"' + t.replace('"','""') + '"' for t in terms))
            for token in tokens:
                conditions.append('instr(files.fold,?)>0')
                args.append(token)
            sql = 'SELECT path,name,kind FROM ' + source + ' WHERE ' + ' AND '.join(conditions)
            sql += ' ORDER BY (files.fold=?) DESC,(instr(files.fold,?)=1) DESC,length(name),name LIMIT ?'
            args.extend([' '.join(tokens),tokens[0],limit])
            return db.execute(sql,args).fetchall()

class DoubleTap:
    """Trigger only on two short, standalone Ctrl releases."""
    def __init__(self):
        self.down = False
        self.started = 0
        self.last = -10
        self.dirty = False
    def update(self, ctrl, other, now):
        fired = False
        if ctrl and not self.down:
            self.started = now
            self.dirty = other
        if other:
            self.dirty = True
            self.last = -10
        if self.down and not ctrl:
            if not self.dirty and now-self.started < .35:
                if now-self.last < .42:
                    fired = True
                    self.last = -10
                else:
                    self.last = now
            else:
                self.last = -10
        self.down = ctrl
        return fired
