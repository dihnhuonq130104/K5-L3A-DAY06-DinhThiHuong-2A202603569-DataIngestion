import unittest
from types import SimpleNamespace
from unittest.mock import patch
from starter.src.hybrid import HybridRanker, tokens
from starter.src.chat import GroundedChat, check_citations


class HybridAndChatTests(unittest.TestCase):
    def setUp(self):
        self.hits=[{'chunk_id':'a','text':'A loop uses continue to skip execution.',
                    'metadata':{'page':139,'printed_page':129,'chapter':'Loops'},'score':0.4},
                   {'chunk_id':'b','text':'An operator compares two values with ==.',
                    'metadata':{'page':98,'printed_page':88,'chapter':'Decisions'},'score':0.8}]

    def test_bilingual_tokenization_and_python_operators(self):
        self.assertIn('loop',tokens('VÒNG LẶP while'))
        self.assertIn('!=',tokens('x != y'))
        self.assertIn('**',tokens('Lũy thừa **'))
        self.assertNotIn('u',tokens('thừa'))

    def test_hybrid_keyword_ranking_filters_and_no_match(self):
        ranker=HybridRanker(self.hits)
        dense=list(reversed(self.hits))
        self.assertEqual(ranker.search('continue',dense,dense_weight=0.25)[0]['chunk_id'],'a')
        self.assertEqual(ranker.search('continue',dense,chapter='Decisions')[0]['chunk_id'],'b')
        self.assertEqual(ranker.search('xyzunknown',dense),dense)
        self.assertEqual(ranker.search('continue',dense,dense_weight=1),dense)

    def test_citations_require_exact_authorized_page_pairs(self):
        self.assertTrue(check_citations('Dùng continue. [PDF p.139; printed p.129]',self.hits))
        self.assertFalse(check_citations('Dùng continue. [PDF p.139; printed p.88]',self.hits))
        self.assertFalse(check_citations('Bằng chứng [PDF p.999; printed p.989]',self.hits))
        self.assertFalse(check_citations('Không có citation',self.hits))

    def test_chat_rejects_incomplete_or_invalid_citations_and_preserves_usage(self):
        for status,text,expected in [
            ('completed','Bằng chứng [PDF p.139; printed p.129]','passed'),
            ('completed','Bằng chứng [PDF p.999; printed p.989]','rejected_or_insufficient'),
            ('incomplete','Bằng chứng [PDF p.139; printed p.129]','rejected_or_insufficient')]:
            response=SimpleNamespace(status=status,output_text=text,
                                     usage=SimpleNamespace(model_dump=lambda:{'input_tokens':1,'output_tokens':2}))
            with patch('starter.src.chat.create_client') as client:
                client.return_value.responses.create.return_value=response
                result=GroundedChat().answer('why?',self.hits)
            self.assertEqual(result['citation_check'],expected)
            self.assertEqual(result['usage']['input_tokens'],1)
            if expected!='passed':self.assertNotIn('999',result['answer'])


if __name__=='__main__':unittest.main()
