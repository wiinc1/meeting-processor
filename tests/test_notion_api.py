import unittest
import sys
import os
from unittest.mock import patch

# Add the parent directory to the path so we can import the project modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from notion_api import NotionAPI

class TestNotionAPI(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Create Notion API with a fake token
        self.api = NotionAPI("fake_api_token")

    def test_helper_methods(self):
        """Test the helper methods for creating Notion blocks."""
        # Test heading block creation
        heading = self.api._create_heading_block("Test Heading", level=2)
        self.assertEqual(heading['type'], 'heading_2')
        self.assertEqual(heading['heading_2']['rich_text'][0]['text']['content'], "Test Heading")
        
        # Test paragraph block creation
        paragraph = self.api._create_paragraph_block("Test paragraph content")
        self.assertEqual(paragraph['type'], 'paragraph')
        self.assertEqual(paragraph['paragraph']['rich_text'][0]['text']['content'], "Test paragraph content")
        
        # Test to-do block creation
        todo = self.api._create_to_do_block("Test todo", checked=True)
        self.assertEqual(todo['type'], 'to_do')
        self.assertEqual(todo['to_do']['rich_text'][0]['text']['content'], "Test todo")
        self.assertTrue(todo['to_do']['checked'])
        
        # Test callout block creation
        callout = self.api._create_callout_block("Test callout", emoji="🚀")
        self.assertEqual(callout['type'], 'callout')
        self.assertEqual(callout['callout']['rich_text'][0]['text']['content'], "Test callout")
        self.assertEqual(callout['callout']['icon']['emoji'], "🚀")

    def test_text_cleaning(self):
        """Test text cleaning functionality."""
        # Test with null bytes
        dirty_text = "This has a null byte\x00 in it"
        clean_text = self.api._clean_text(dirty_text)
        self.assertNotIn('\x00', clean_text)
        
        # Test with extra whitespace
        whitespace_text = "  Too   many    spaces   "
        clean_text = self.api._clean_text(whitespace_text)
        self.assertEqual(clean_text, "Too many spaces")
        
        # Test with None value
        self.assertEqual(self.api._clean_text(None), "")
        
        # Test with non-string value
        self.assertIsInstance(self.api._clean_text(123), str)

if __name__ == '__main__':
    unittest.main() 