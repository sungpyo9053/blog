import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

def load(name):
    path=Path(__file__).parent/(name+'-example.py')
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

pagination=load('pagination');summary=load('summary')

class ReaderExamples(unittest.TestCase):
    def test_pagination_cases(self):
        cases=[
            ('empty',[(0,0,[])],True),
            ('exact_multiple',[(6,2,[{'id':i} for i in (1,2,3)]),(6,2,[{'id':i} for i in (4,5,6)])],True),
            ('duplicate',[(4,2,[{'id':i} for i in (1,2,3)]),(4,2,[{'id':3}])],False),
            ('changed_total',[(4,2,[{'id':i} for i in (1,2,3)]),(5,2,[{'id':4},{'id':5}])],False),
            ('short_first',[(4,2,[{'id':1}])],False),
            ('bool_id',[(1,1,[{'id':True}])],False),
            ('wrong_pages',[(4,1,[{'id':1}])],False)]
        for name,rows,expected in cases:
            with self.subTest(name=name):
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        pagination.collect(lambda page,size:rows[page-1])
                    passed=True
                except ValueError:passed=False
                self.assertEqual(passed,expected)

    def test_summary_cases(self):
        cases=[
            ('single','<h2>20초 <em>핵심</em> 요약</h2>',(1,0)),
            ('duplicate','<h2>핵심 요약</h2><h2>20초 핵심 요약</h2>',(2,0)),
            ('escaped_code','<pre><code>&lt;h2&gt;핵심 요약&lt;/h2&gt;</code></pre>',(0,0)),
            ('box','<div class="a huntlab-article-quick-summary b"></div>',(0,1)),
            ('script','<script>"<h2>핵심 요약</h2>"</script>',(0,0))]
        for name,body,expected in cases:
            with self.subTest(name=name):
                parser=summary.SummaryCounter();parser.feed(body);parser.close()
                self.assertEqual((parser.headings,parser.boxes),expected)

if __name__=='__main__':unittest.main()
