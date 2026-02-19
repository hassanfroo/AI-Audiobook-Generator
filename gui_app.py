import os
import asyncio
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from audiobook_gen import AudiobookGenerator

class AudiobookGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Audiobook Generator")
        self.geometry("650x550")
        
        # Set theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # UI Elements
        self.label = ctk.CTkLabel(self, text="AI Audiobook Generator", font=("Inter", 24, "bold"))
        self.label.pack(pady=20)

        # File Selection
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(pady=10, padx=20, fill="x")
        
        self.file_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Select a PDF or TXT file...")
        self.file_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        
        self.browse_button = ctk.CTkButton(self.file_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side="right", padx=10, pady=10)

        # Voice Selection
        self.voice_label = ctk.CTkLabel(self, text="Select Voice (British English):")
        self.voice_label.pack(pady=(15, 0))
        
        self.voices = {
            "Sonia: Female, Adult (Calm/Professional)": "en-GB-SoniaNeural",
            "Ryan: Male, Adult (Clear/Informative)": "en-GB-RyanNeural",
            "Libby: Female, Adult (Middle-aged/Warm)": "en-GB-LibbyNeural",
            "Maisie: Female, Teen (Lively/Bright)": "en-GB-MaisieNeural",
            "Thomas: Male, Adult (Deep/Formal)": "en-GB-ThomasNeural"
        }
        self.voice_var = ctk.StringVar(value="Sonia: Female, Adult (Calm/Professional)")
        self.voice_dropdown = ctk.CTkOptionMenu(self, values=list(self.voices.keys()), variable=self.voice_var, width=300)
        self.voice_dropdown.pack(pady=10)

        # Export Options Frame
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, padx=20, fill="x")

        self.export_mode_var = ctk.StringVar(value="single")
        self.single_radio = ctk.CTkRadioButton(self.options_frame, text="Full Audiobook", variable=self.export_mode_var, value="single")
        self.single_radio.pack(side="left", padx=20, pady=10)
        
        self.chapter_radio = ctk.CTkRadioButton(self.options_frame, text="Chapter by Chapter", variable=self.export_mode_var, value="chapters")
        self.chapter_radio.pack(side="left", padx=20, pady=10)

        # Output Folder Selection
        self.out_frame = ctk.CTkFrame(self)
        self.out_frame.pack(pady=10, padx=20, fill="x")
        
        self.out_entry = ctk.CTkEntry(self.out_frame, placeholder_text="Choose saving folder (Optional)...")
        self.out_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        
        self.out_browse_button = ctk.CTkButton(self.out_frame, text="Save To", command=self.browse_folder)
        self.out_browse_button.pack(side="right", padx=10, pady=10)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(pady=15, padx=20, fill="x")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="Ready", font=("Inter", 12))
        self.status_label.pack(pady=5)

        # Generate Button
        self.generate_button = ctk.CTkButton(self, text="Generate Audiobook", command=self.start_generation, height=40, font=("Inter", 16, "bold"))
        self.generate_button.pack(pady=20)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[
            ("Documents", "*.pdf *.docx *.md *.txt"), 
            ("PDF", "*.pdf"), 
            ("Word", "*.docx"), 
            ("Markdown", "*.md"), 
            ("Text", "*.txt")
        ])
        if filename:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, filename)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, folder)

    def update_progress(self, value):
        self.progress_bar.set(value)
        self.status_label.configure(text=f"Processing... {int(value * 100)}%")

    def start_generation(self):
        input_path = self.file_entry.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid file.")
            return

        voice_name = self.voice_var.get()
        voice_id = self.voices[voice_name]
        export_mode = self.export_mode_var.get()
        output_dir = self.out_entry.get()
        
        self.generate_button.configure(state="disabled")
        self.browse_button.configure(state="disabled")
        self.out_browse_button.configure(state="disabled")
        self.status_label.configure(text="Starting...")
        
        # Run the async generation in a separate thread
        threading.Thread(target=self.run_async_gen, args=(input_path, voice_id, export_mode, output_dir), daemon=True).start()

    def run_async_gen(self, input_path, voice_id, export_mode, output_dir):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if not output_dir:
            output_dir = os.path.dirname(input_path)
            
        gen = AudiobookGenerator(voice=voice_id)
        
        try:
            # Step 1: Extract Text
            self.status_label.configure(text="Extracting text...")
            ext = os.path.splitext(input_path)[1].lower()
            if ext == ".pdf":
                text = gen.extract_text_from_pdf(input_path)
            elif ext == ".docx":
                text = gen.extract_text_from_docx(input_path)
            else:
                with open(input_path, 'r', encoding='utf-8') as f:
                    text = gen.cleaner.clean_text(f.read())
            
            if not text:
                raise ValueError("No text extracted.")

            # Step 2: Determine Output Strategy
            if export_mode == "chapters":
                chapters = gen.split_into_chapters(text)
                total_chapters = len(chapters)
                self.status_label.configure(text=f"Found {total_chapters} chapters...")
                
                for i, (title, content) in enumerate(chapters):
                    # Sanitize title for filename
                    safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).rstrip()
                    # If intro is empty, skip
                    if not content.strip(): continue
                    
                    self.status_label.configure(text=f"Generating Chapter {i+1}/{total_chapters}: {safe_title}")
                    out_name = f"{i+1:02d}_{safe_title}.mp3"
                    out_path = os.path.join(output_dir, out_name)
                    
                    # Nested progress (simple)
                    def chapter_progress(v):
                        overall = (i / total_chapters) + (v / total_chapters)
                        self.update_progress(overall)

                    loop.run_until_complete(gen.generate_audio(content, out_path, progress_callback=chapter_progress))
            else:
                output_path = os.path.join(output_dir, os.path.splitext(os.path.basename(input_path))[0] + ".mp3")
                loop.run_until_complete(gen.generate_audio(text, output_path, progress_callback=self.update_progress))
            
            self.status_label.configure(text="Success! Audiobook saved.")
            messagebox.showinfo("Success", f"Audiobooks saved in:\n{output_dir}")
            
        except Exception as e:
            self.status_label.configure(text="Error occurred.")
            messagebox.showerror("Error", str(e))
        
        finally:
            self.generate_button.configure(state="normal")
            self.browse_button.configure(state="normal")
            self.out_browse_button.configure(state="normal")
            self.progress_bar.set(0)
            self.status_label.configure(text="Ready")
            loop.close()

if __name__ == "__main__":
    app = AudiobookGUI()
    app.mainloop()
