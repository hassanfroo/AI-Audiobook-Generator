import os
import re
import asyncio
import pymupdf
import edge_tts
import docx
from tqdm import tqdm
from text_cleaner import TextCleaner

class AudiobookGenerator:
    def __init__(self, voice="en-GB-SoniaNeural"):
        self.voice = voice
        self.cleaner = TextCleaner()

    def extract_text_from_pdf(self, pdf_path):
        """Extracts and cleans text from a PDF file."""
        print(f"Extracting text from {os.path.basename(pdf_path)}...")
        doc = pymupdf.open(pdf_path)
        full_text = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            full_text += text + "\n"
            
        doc.close()
        return self.cleaner.clean_text(full_text)

    def extract_text_from_docx(self, docx_path):
        """Extracts and cleans text from a DOCX file."""
        print(f"Extracting text from {os.path.basename(docx_path)}...")
        doc = docx.Document(docx_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return self.cleaner.clean_text("\n\n".join(full_text))

    def split_into_chapters(self, text):
        """
        Simple heuristic to split text into chapters based on headers.
        Recognizes 'Chapter X', 'Part X', and Markdown '#' headers.
        """
        paragraphs = text.split('\n\n')
        chapters = []
        current_chapter_title = "Intro"
        current_chapter_content = []

        # Patterns for conventional and markdown headers
        chapter_pattern = re.compile(r'^(Chapter|Part|Section)\s+[\dIVX]+.*', re.IGNORECASE)
        md_header_pattern = re.compile(r'^#+\s+(.*)', re.MULTILINE)

        for p in paragraphs:
            p_strip = p.strip()
            is_chapter = False
            title = p_strip

            # Check for conventional chapter pattern
            if chapter_pattern.match(p_strip):
                is_chapter = True
            else:
                # Check for Markdown header pattern
                md_match = md_header_pattern.match(p_strip)
                if md_match:
                    is_chapter = True
                    title = md_match.group(1) # Extract text without # symbols

            if is_chapter:
                if current_chapter_content:
                    chapters.append((current_chapter_title, "\n\n".join(current_chapter_content)))
                current_chapter_title = title
                current_chapter_content = []
            else:
                # Still clean the line if it has any rogue # (though usually caught by md_match)
                cleaned_line = re.sub(r'^#+\s+', '', p_strip)
                current_chapter_content.append(cleaned_line)
        
        if current_chapter_content:
            chapters.append((current_chapter_title, "\n\n".join(current_chapter_content)))
            
        return chapters

    async def generate_audio(self, text, output_path, progress_callback=None):
        """Generates MP3 audio from text using edge-tts with progress updates."""
        # Split text into chunks by paragraph to provide progress updates
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paragraphs: # Fallback if no double newlines
            paragraphs = [text]
            
        total_chunks = len(paragraphs)
        print(f"Generating audio to {output_path} ({total_chunks} chunks)...")
        
        # We'll use a temporary file to collect chunks or just one communicate if preferred.
        # However, to give real progress, we should really be streaming or doing chunks.
        # Actually, for the best audio quality (prosody), one large block is often better,
        # but edge-tts has limits. Let's do a balanced approach: 5000 char chunks.
        
        chunks = []
        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk) + len(p) < 4000:
                current_chunk += p + "\n\n"
            else:
                chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"
        if current_chunk:
            chunks.append(current_chunk.strip())

        total_chunks = len(chunks)
        
        # Initialize the output file
        with open(output_path, "wb") as f:
            for i, chunk in enumerate(chunks):
                communicate = edge_tts.Communicate(chunk, self.voice)
                async for sub_chunk in communicate.stream():
                    if sub_chunk["type"] == "audio":
                        f.write(sub_chunk["data"])
                
                if progress_callback:
                    progress_callback((i + 1) / total_chunks)
        
        print(f"Audiobook saved successfully at: {output_path}")

async def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python audiobook_gen.py <input_file> [output_path_or_dir] [--chapters]")
        return

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    chapter_mode = "--chapters" in sys.argv

    gen = AudiobookGenerator()

    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".pdf":
        text = gen.extract_text_from_pdf(input_path)
    elif ext == ".docx":
        text = gen.extract_text_from_docx(input_path)
    else:
        with open(input_path, 'r', encoding='utf-8') as f:
            text = gen.cleaner.clean_text(f.read())

    if not text:
        print("Error: No text extracted.")
        return

    if chapter_mode:
        chapters = gen.split_into_chapters(text)
        out_dir = output_path or "."
        for i, (title, content) in enumerate(chapters):
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).rstrip()
            if not content.strip(): continue
            out_file = os.path.join(out_dir, f"{i+1:02d}_{safe_title}.mp3")
            await gen.generate_audio(content, out_file)
    else:
        final_out = output_path or os.path.splitext(input_path)[0] + ".mp3"
        await gen.generate_audio(text, final_out)

if __name__ == "__main__":
    asyncio.run(main())
