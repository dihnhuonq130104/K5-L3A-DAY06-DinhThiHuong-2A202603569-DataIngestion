import unittest
import tempfile
import subprocess
import sys
from pathlib import Path
from starter.src.models import DocumentPage
from starter.src.ingestion import normalize_text
from starter.src.chunking import fixed_size, by_paragraph
from starter.src.evaluation import evaluate_query
from starter.src.chroma_store import ChromaStore


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.page=DocumentPage('book','source',96,'A complete sentence.\nAnother complete idea.\n  print(1)\n'*20,{'chapter':'Decisions'})

    def test_normalization_preserves_code(self):
        text=normalize_text('cafe\u0301\nif True:\n    print(1)\nAccess for free at openstax.org')
        self.assertIn('café',text)
        self.assertIn('    print(1)',text)
        self.assertNotIn('Access for free',text)

    def test_fixed_coverage_and_stable_ids(self):
        chunks=fixed_size(self.page,100,20)
        covered=set()
        for c in chunks:
            covered.update(range(c.metadata['char_start'],c.metadata['char_end']))
            self.assertEqual(c.text,self.page.text[c.metadata['char_start']:c.metadata['char_end']])
        self.assertEqual(covered,set(range(len(self.page.text))))
        self.assertEqual([c.chunk_id for c in chunks],[c.chunk_id for c in fixed_size(self.page,100,20)])
        with self.assertRaises(ValueError):fixed_size(self.page,100,100)

    def test_paragraph_coverage_and_limit(self):
        chunks=by_paragraph(self.page,100)
        self.assertEqual(''.join(c.text for c in chunks),self.page.text)
        self.assertTrue(all(len(c.text)<=100 for c in chunks))
        self.assertTrue(all(c.page==96 and c.metadata['chapter']=='Decisions' for c in chunks))

    def test_metric_needs_full_evidence_and_source(self):
        question={'id':'q','split':'test','question':'why','expected_answer':'answer','gold_source_id':'book','gold_page':96,'evidence_quote':'whole evidence'}
        hit=lambda text,source='book':{'text':text,'metadata':{'document_id':source,'page':96}}
        result=evaluate_query(question,[hit('whole'),hit('whole\n evidence'),hit('whole evidence','wrong')])
        self.assertFalse(result['hit1']);self.assertTrue(result['hit3'])
        self.assertEqual(result['hit_labels'],[False,True,False])

    def test_store_reload_removes_obsolete_and_filters(self):
        base=Path('tmp/tests');base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base,ignore_cleanup_errors=True) as folder:
            store=ChromaStore(Path(folder),'test-collection',2)
            chunks=fixed_size(self.page,100,20)[:2]
            store.replace(chunks,[[1.,0.],[0.,1.]])
            store.replace(chunks,[[1.,0.],[0.,1.]])
            self.assertEqual(store.collection.count(),2)
            store.replace(chunks[:1],[[1.,0.]])
            self.assertEqual(store.collection.count(),1)
            self.assertEqual(store.search([1.,0.],filters={'chapter':'Loops'}),[])
            self.assertEqual(store.search([1.,0.],filters={'chapter':'Decisions'})[0]['chunk_id'],chunks[0].chunk_id)
            with self.assertRaises(ValueError):store.search([1.,0.],filters={'page':96})


if __name__=='__main__':unittest.main()
