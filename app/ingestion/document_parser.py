from pathlib import Path
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.docx_parser import parse_docx
from app.ingestion.excel_parser import parse_xlsx
from app.ingestion.text_parser import parse_txt

PARSERS={".pdf":parse_pdf,".docx":parse_docx,".xlsx":parse_xlsx,".txt":parse_txt}
def parse_document(path):
    ext=Path(path).suffix.lower()
    if ext not in PARSERS: raise ValueError("Supported formats: PDF, DOCX, XLSX, TXT")
    return PARSERS[ext](path)
