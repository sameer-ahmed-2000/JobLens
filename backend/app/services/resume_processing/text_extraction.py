import io
import pdfplumber
import docx

def extract_text_pdf(file_bytes: bytes) -> str:
    """
    Extracts plain text from PDF bytes using pdfplumber.
    """
    text = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n".join(text).strip()

def extract_text_docx(file_bytes: bytes) -> str:
    """
    Extracts plain text from DOCX bytes using python-docx.
    Traverses both standard paragraphs and table cells to capture all details.
    """
    doc = docx.Document(io.BytesIO(file_bytes))
    text = []
    
    # 1. Extract standard paragraphs
    for para in doc.paragraphs:
        if para.text.strip():
            text.append(para.text)
            
    # 2. Extract text inside tables (resumes often use tables for layout)
    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                # Deduplicate/clean text inside cell
                cell_text = cell.text.strip()
                if cell_text and cell_text not in row_text:
                    row_text.append(cell_text)
            if row_text:
                text.append(" | ".join(row_text))
                
    return "\n".join(text).strip()
