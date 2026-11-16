import unittest
from unittest.mock import mock_open, patch
from app.ingestion.faq_extractor import extract_faqs
from app.ingestion.document_parser import parse_document
from app.ingestion.text_parser import parse_txt
from app.knowledge.chunking import chunk_text

class IngestionUnitTests(unittest.TestCase):
    def test_jsonld_faq_preserves_content(self):
        html='''<html><head><title>Visitor FAQs</title><script type="application/ld+json">{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"How do I register?","acceptedAnswer":{"@type":"Answer","text":"Enter your details."}}]}</script></head></html>'''
        found=extract_faqs(html,"https://example.org/faq")
        self.assertEqual(found[0]["question"],"How do I register?")
        self.assertEqual(found[0]["answer"],"Enter your details.")

    def test_dom_faq_extraction(self):
        html="<main><h2>How does visitor check-in work?</h2><p>Visitors enter their details.</p></main>"
        self.assertEqual(extract_faqs(html,"https://example.org")[0]["answer"],"Visitors enter their details.")

    def test_text_parser_and_chunking(self):
        with patch("builtins.open",mock_open(read_data="Question: How long?\nAnswer: Two days.")):
            rows=parse_txt("faq.txt")
        self.assertIn("How long?",rows[0]["text"])
        pieces=chunk_text("a"*100,40,10)
        self.assertTrue(all(len(x)<=40 for x in pieces)); self.assertGreater(len(pieces),1)

    def test_rejects_unknown_extension(self):
        with self.assertRaises(ValueError): parse_document("file.exe")

if __name__ == "__main__": unittest.main()
