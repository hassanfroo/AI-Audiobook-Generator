import re

class TextCleaner:
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Cleans text for TTS by removing common academic clutter like citations, 
        excessive whitespace, and non-pronounceable symbols.
        """
        # 1. Remove citations in brackets like [1], [12, 13], [1-5]
        text = re.sub(r'\[\d+(?:,\s*\d+|-\d+)*\]', '', text)
        
        # 2. Remove citations in parentheses like (Smith, 2020), (Jones et al., 2019)
        # This is a bit trickier to avoid hitting normal parenthetical remarks.
        # We look for (Name, Year) patterns.
        text = re.sub(r'\((?:[A-Z][a-z]+(?:\set\sal\.)?,\s*\d{4})\)', '', text)
        
        # 3. Remove URLs
        text = re.sub(r'https?://[^\s<>"]+|www\.[^\s<>"]+', '', text)
        
        # 4. Normalize whitespace (preserve double newlines for paragraph/chapter logic)
        text = re.sub(r'[ \t]+', ' ', text) # Normalize spaces/tabs
        text = re.sub(r'\n\s*\n', '\n\n', text) # Normalize multiple newlines to exactly two
        
        # Protect headers and lists from being joined with previous/next lines
        # We only join a line with the next if it doesn't look like a header, list, or blockquote
        lines = text.split('\n')
        processed_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                processed_lines.append("")
                continue
            
            # If current line starts a header, list, or blockquote, keep it as a new paragraph
            if re.match(r'^(#+\s+|[*+-]\s+|>\s+|\d+\.\s+)', stripped):
                processed_lines.append("\n" + stripped + "\n")
            else:
                processed_lines.append(stripped)
        
        text = " ".join(processed_lines)
        text = re.sub(r'\s*\n\s*', '\n', text) # Clean up intermediate newlines
        text = re.sub(r'\n+', '\n\n', text) # Ensure consistent double newlines for paragraphs
        text = text.strip()
        
        # 5. Fix hyphenated words broken by line breaks (e.g., "en- \ngineering" -> "engineering")
        text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
        
        # 6. Markdown syntax cleaning (without removing headers entirely, just the symbols)
        # Remove bold, italics, strikethrough
        text = re.sub(r'(\*\*|__|~~|\*|_)(\S.*?\S)\1', r'\2', text)
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        # Remove inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Remove links: [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove images
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # Remove blockquotes
        text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)
        
        # 7. Remove standalone page numbers or figure/table references
        text = re.sub(r'Page \d+', '', text)
        text = re.sub(r'Figure \d+[:.]?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Table \d+[:.]?', '', text, flags=re.IGNORECASE)

        return text

if __name__ == "__main__":
    # Quick test
    sample = """
    This is an example academic text [1, 2]. As noted by Smith et al. (Smith et al., 2020), 
    the results are signifi-
    cant. See Figure 1 for more details. Visit www.example.com for info.
    """
    cleaner = TextCleaner()
    cleaned = cleaner.clean_text(sample)
    print(f"Original: {sample}")
    print(f"Cleaned: {cleaned}")
