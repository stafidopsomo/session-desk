import copy,json,tempfile,unittest
from pathlib import Path
from sessiondesk.importer import Library,UserError
from sessiondesk.store import Store
from tests.fixtures import make_library

class ReferenceBookTests(unittest.TestCase):
    def test_book_wrapper_assets_identity_and_portable_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);root=make_library(base/'library',rich=True)
            original=Library(root).load('DEMO')[0]
            (root/'data/books.json').write_text(json.dumps({'book':[{'id':'DEMO','name':'Original Field Guide'}]}),encoding='utf-8')
            (root/'data/book').mkdir();raw=json.loads((root/'data/adventure/adventure-demo.json').read_text(encoding='utf-8'))
            (root/'data/book/book-demo.json').write_text(json.dumps({'bookData':[{'id':'DEMO','data':raw['data']}]}),encoding='utf-8')
            library=Library(root);self.assertEqual(len(library.inventory()),2)
            book,blobs=library.load('book:DEMO');self.assertEqual(book['source_kind'],'book');self.assertEqual(book['source'],'DEMO')
            self.assertNotEqual(book['id'],original['id']);self.assertEqual(library.load('DEMO')[0],original)
            self.assertEqual(book['book'],raw['data']);self.assertTrue(book['maps']);self.assertTrue(book['pictures'])
            store=Store(base/'profile');wid=store.create('Original field study')['id'];store.import_graph(wid,book,blobs)
            store.prepare(wid,book['id'],book['entries'][0]['id'],{'translation':'Original narration','notes':'Private note','status':'draft'})
            backup=base/'backup.zip';store.backup_file(wid,backup)
            other=Store(base/'restored');restored=other.restore_file(backup)
            out=other.adventure(restored['id'],book['id']);self.assertEqual(out['source_kind'],'book');self.assertEqual(out['book'],book['book'])
    def test_book_traversal_and_mismatched_wrapper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=make_library(temp);library=Library(root)
            with self.assertRaises(UserError):library.source_path('book:../../bad')
            (root/'data/books.json').write_text(json.dumps({'book':[{'id':'DEMO','name':'Original reference'}]}),encoding='utf-8')
            (root/'data/book').mkdir();(root/'data/book/book-demo.json').write_text(json.dumps({'bookData':[{'id':'OTHER','data':[{'name':'Wrong source'}]}]}),encoding='utf-8')
            with self.assertRaises(UserError):library.load('book:DEMO')
