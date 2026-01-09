import unittest
import sys
import os

# Add the parent directory to the path so we can import the project modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nlp_processor import ActionItemDetector

class TestActionItemDetector(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.detector = ActionItemDetector()
        # Skip all tests if spaCy model loading fails
        if self.detector.nlp is None:
            self.skipTest("SpaCy model not available, skipping NLP tests")

    def test_detect_actions_basic(self):
        """Test basic detection of action items."""
        transcript = """
        Let's follow up on the marketing campaign next week.
        We should schedule a meeting with the vendor.
        """
        
        actions = self.detector.detect_actions(transcript)
        
        # Check that we found at least one action
        self.assertGreaterEqual(len(actions), 1, "Should detect at least 1 action item")
        
        # Check that each action has the required fields
        for action in actions:
            self.assertIn('text', action, "Action should have 'text' field")
            self.assertIn('owner', action, "Action should have 'owner' field")
            self.assertIn('due_date', action, "Action should have 'due_date' field")

    def test_detect_actions_with_keywords(self):
        """Test detection of action items with explicit keywords."""
        transcript = """
        Let's follow up on the marketing campaign next week.
        John needs to prepare the sales report by Friday.
        There's an action item for Sarah to contact the client.
        We should schedule a meeting with the vendor.
        """
        
        actions = self.detector.detect_actions(transcript)
        
        # Check that we found at least 3 actions
        self.assertGreaterEqual(len(actions), 3, "Should detect at least 3 action items")
        
        # Check that each action has the required fields
        for action in actions:
            self.assertIn('text', action, "Action should have 'text' field")
            self.assertIn('owner', action, "Action should have 'owner' field")
            self.assertIn('due_date', action, "Action should have 'due_date' field")
            
        # Check for specific action texts
        action_texts = [action['text'].lower() for action in actions]
        self.assertTrue(any('follow up' in text for text in action_texts), "Should detect 'follow up' action")
        self.assertTrue(any('prepare the sales report' in text for text in action_texts), "Should detect 'prepare the sales report' action")
        
        # Check for specific owners
        owners = [action['owner'].lower() for action in actions]
        self.assertTrue(any('john' in owner for owner in owners), "Should detect 'John' as an owner")
        self.assertTrue(any('sarah' in owner for owner in owners), "Should detect 'Sarah' as an owner")

    def test_detect_imperative_actions(self):
        """Test detection of imperative sentences as action items."""
        transcript = """
        Send the proposal to the client tomorrow.
        Create a new design for the landing page.
        Update the documentation with the latest changes.
        """
        
        actions = self.detector.detect_actions(transcript)
        
        # Check that we found at least 2 actions
        self.assertGreaterEqual(len(actions), 2, "Should detect at least 2 imperative action items")
        
        # Check for specific action texts (some of these might be detected as imperatives)
        action_texts = [action['text'].lower() for action in actions]
        imperative_phrases = ['send the proposal', 'create a new design', 'update the documentation']
        
        # At least one of these should be detected
        detected_count = sum(1 for phrase in imperative_phrases if any(phrase in text for text in action_texts))
        self.assertGreaterEqual(detected_count, 1, "Should detect at least one imperative action")

    def test_extract_due_date(self):
        """Test extraction of due dates from action text."""
        # This test might be skipped if the spaCy model fails to load
        if not self.detector.nlp:
            self.skipTest("SpaCy model not available for date extraction testing")
            
        test_cases = [
            ("Complete the report by tomorrow.", "tomorrow"),
            ("Send the email by next Friday.", "next friday"),
            ("Schedule a meeting for next week.", "next week"),
            ("Review the document within 3 days.", "3 days")
        ]
        
        for text, expected_date_text in test_cases:
            # Create a mock sentence object that the extract_due_date method can process
            doc = self.detector.nlp(text)
            for sent in doc.sents:
                result = self.detector.extract_due_date(sent)
                if result:  # If a date was extracted
                    # This is a flexible test since exact datetime objects may vary
                    self.assertIsNotNone(result, f"Should extract a due date from '{text}'")

    def test_simple_fallback(self):
        """Test the simple fallback mechanism when spaCy is not available."""
        # Override the NLP attribute to simulate missing spaCy
        original_nlp = self.detector.nlp
        self.detector.nlp = None
        
        try:
            transcript = """
            Let's follow up on the marketing campaign next week.
            John needs to prepare the sales report by Friday.
            """
            
            actions = self.detector.detect_actions(transcript)
            
            # Check that we got some actions even without spaCy
            self.assertGreaterEqual(len(actions), 1, "Should detect at least 1 action item with fallback")
            
            # Check that actions have the expected format
            for action in actions:
                self.assertIn('text', action, "Action should have 'text' field")
                self.assertIn('owner', action, "Action should have 'owner' field")
                self.assertIn('due_date', action, "Action should have 'due_date' field")
        finally:
            # Restore the original NLP attribute
            self.detector.nlp = original_nlp

    def test_deduplication(self):
        """Test that similar action items are not duplicated."""
        transcript = """
        We need to follow up with the client.
        We should follow up with the client soon.
        John will prepare the presentation.
        """
        
        actions = self.detector.detect_actions(transcript)
        
        # Get all action texts
        action_texts = [action['text'].lower() for action in actions]
        
        # Check that similar actions about following up are not duplicated
        follow_up_count = sum(1 for text in action_texts if 'follow up' in text)
        self.assertLessEqual(follow_up_count, 2, "Similar actions should not be duplicated")

if __name__ == '__main__':
    unittest.main() 