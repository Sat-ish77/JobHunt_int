"""
Resume parser — extracts text from PDF and DOCX uploaded files.
Uses pdfplumber for PDFs and python-docx for DOCX files.
"""

import os
import tempfile
import pdfplumber
from docx import Document


def parse_resume(uploaded_file) -> str:
    """
    Parse a Streamlit UploadedFile (PDF or DOCX) and return clean text.
    Raises ValueError if fewer than 100 characters are extracted.
    """
    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name.lower()
    tmp_path = None

    try:
        # Determine extension
        if file_name.endswith(".pdf"):
            suffix = ".pdf"
        elif file_name.endswith(".docx"):
            suffix = ".docx"
        else:
            raise ValueError(
                "Unsupported file type. Please upload a PDF or DOCX file."
            )

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Extract text
        text = ""
        if suffix == ".pdf":
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif suffix == ".docx":
            doc = Document(tmp_path)
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"

        text = text.strip()

        if len(text) < 100:
            raise ValueError(
                "Could not extract text. "
                "Try copy-pasting your resume as text."
            )

        return text

    except ValueError:
        raise
    except Exception as e:
        print(f"[parse_resume] Error: {e}")
        raise ValueError(
            f"Error parsing resume: {e}. "
            "Try copy-pasting your resume as text."
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

