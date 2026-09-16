import io
import PyPDF2

def extract_text_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Extracts text from a PDF, keeping track of page numbers.
    Returns a list of dicts: [{"page": 1, "text": "..."}]
    """
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text = page.extract_text()
        if text:
            pages.append({
                "page": page_num + 1,
                "text": text.strip()
            })
            
    return pages

def chunk_text(pages: list[dict], chunk_size: int = 1000, overlap: int = 200) -> list[dict]:
    """
    Splits page text into smaller chunks. 
    Very simplistic chunking for demonstration purposes.
    """
    chunks = []
    for page in pages:
        text = page["text"]
        page_num = page["page"]
        
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text_content = text[start:end]
            
            # Count tokens (approximate 4 chars per token)
            token_count = len(chunk_text_content) // 4
            
            chunks.append({
                "content": chunk_text_content,
                "page_number": page_num,
                "token_count": token_count
            })
            
            start += (chunk_size - overlap)
            
    return chunks
