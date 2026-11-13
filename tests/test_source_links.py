import unittest
from starter.src.source_links import source_links, page_sections


class SourceLinkTests(unittest.TestCase):
    def hit(self, page, start, end):
        text=page_sections()[page][0]
        return {'metadata':{'page':page,'char_start':start,'char_end':end},'text':text[start:end]}

    def test_same_pdf_page_two_sections_and_crossing_chunk(self):
        self.assertTrue(source_links(self.hit(100,0,700))[0][1].endswith('4-1-boolean-values'))
        self.assertTrue(source_links(self.hit(100,724,1000))[0][1].endswith('4-2-if-else-statements'))
        self.assertEqual(len(source_links(self.hit(100,650,900))),2)
        self.assertTrue(source_links(self.hit(140,633,900))[0][1].endswith('5-5-loop-else'))
        self.assertTrue(source_links(self.hit(140,0,633))[0][1].endswith('5-4-break-and-continue'))

    def test_selected_page_ranges_and_legacy_hit(self):
        for page,(text,spans) in page_sections().items():
            self.assertEqual(spans[0][0],0)
            self.assertEqual(spans[-1][1],len(text))
            links=source_links({'metadata':{'page':page},'text':text})
            self.assertTrue(links)
            self.assertTrue(all('/pages/' in url and '/details/' not in url for _,url in links))
        self.assertTrue(source_links(self.hit(96,0,80))[0][1].endswith('4-1-boolean-values'))
        self.assertTrue(source_links(self.hit(126,0,80))[0][1].endswith('5-1-while-loop'))
        self.assertTrue(source_links(self.hit(139,0,80))[0][1].endswith('5-4-break-and-continue'))


if __name__=='__main__':unittest.main()
