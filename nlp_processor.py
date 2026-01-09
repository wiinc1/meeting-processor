import re
import logging

class ActionItemDetector:
    """A simple detector for action items in meeting transcripts."""
    
    def __init__(self):
        """Initialize the action item detector."""
        self.logger = logging.getLogger(__name__)
        
        # Patterns for detecting action items
        self.action_patterns = [
            r"(?:action item|task|to-?do|action)(?:\s*\d+)?(?:\s*:|\s*-|\s*\*|\s+is|\s+for)?\s*([^.!?]+)[.!?]",
            r"(?:need|needs)\s+to\s+([^.!?]+)[.!?]",
            r"(?:should|must|will|shall)\s+([^.!?]+)[.!?]",
            r"@(\w+)[,\s]+(?:needs?|has)\s+to\s+([^.!?]+)[.!?]",
            r"(?:assigned|assign)\s+to\s+(\w+)[,\s:]?\s*([^.!?]+)[.!?]"
        ]
        
        # Patterns for ignoring false positives
        self.ignore_patterns = [
            r"^I need",
            r"^We need",
            r"^They need",
            r"^not an action",
            r"^no action",
            r"^future action",
            r"^action required$"
        ]
    
    def detect_actions(self, text):
        """
        Detect action items in the text.
        
        Args:
            text (str): Text to analyze for action items
            
        Returns:
            list: List of dictionaries containing action items and metadata
        """
        if not text:
            return []
            
        actions = []
        
        # Split text into paragraphs and analyze each one
        paragraphs = text.split('\n')
        for paragraph in paragraphs:
            # Skip empty paragraphs
            if not paragraph.strip():
                continue
                
            # Check for action items using our patterns
            for pattern in self.action_patterns:
                matches = re.finditer(pattern, paragraph, re.IGNORECASE)
                
                for match in matches:
                    # Get the action text
                    if len(match.groups()) == 1:
                        action_text = match.group(1).strip()
                        owner = "Brian"  # Default owner per requirements
                    elif len(match.groups()) == 2:
                        # We might have captured an owner and action
                        owner_name = match.group(1).strip()
                        action_text = match.group(2).strip()
                        
                        # Store original owner in description but set owner to Brian per requirements
                        description = f"Originally assigned to: {owner_name}" if owner_name.lower() != "brian" else ""
                        owner = "Brian"  # Always assign to Brian
                    else:
                        continue
                    
                    # Skip if too short or matches ignore patterns
                    if len(action_text) < 5:
                        continue
                        
                    # Check against ignore patterns
                    skip = False
                    for ignore in self.ignore_patterns:
                        if re.match(ignore, action_text, re.IGNORECASE):
                            skip = True
                            break
                    
                    if skip:
                        continue
                    
                    # Add to our actions list
                    action = {
                        'text': action_text,
                        'owner': owner,
                    }
                    
                    # Add description if we have an original owner
                    if 'description' in locals() and description:
                        action['description'] = description
                    
                    actions.append(action)
        
        self.logger.info(f"Detected {len(actions)} action items in text")
        return actions 