import unittest
from streamlit.testing.v1 import AppTest


class UITests(unittest.TestCase):
    def test_demo_controls_and_audit_validation(self):
        app=AppTest.from_file('app.py').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs),3)
        self.assertTrue(next(x for x in app.selectbox if x.label=='Chapter scope').disabled)
        strategy=next(x for x in app.selectbox if x.label=='Retrieval strategy')
        self.assertEqual(strategy.value,'B')
        strategy.select('C').run()
        self.assertFalse(app.exception)
        self.assertFalse(next(x for x in app.selectbox if x.label=='Chapter scope').disabled)
        next(x for x in app.selectbox if x.label=='Chapter scope').select('Loops').run()
        self.assertFalse(app.exception)
        app.radio[0].set_value('test').run()
        self.assertTrue(any('8/10' in str(frame.value) for frame in app.dataframe))
        next(b for b in app.button if b.label=='Save review').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Enter a reviewer' in e.value for e in app.error))


if __name__=='__main__':unittest.main()
