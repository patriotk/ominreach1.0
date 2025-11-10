import PyPDF2
import docx
import io
import logging

logger = logging.getLogger(__name__)

class DocumentParser:
    """Parse PDF and DOCX files for product context"""
    
    @staticmethod
    def parse_pdf(file_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"PDF parsing error: {str(e)}")
            return ""
    
    @staticmethod
    def parse_docx(file_content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            docx_file = io.BytesIO(file_content)
            doc = docx.Document(docx_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"DOCX parsing error: {str(e)}")
            return ""
    
    @staticmethod
    def parse_file(filename: str, content: bytes) -> str:
        """Parse file based on extension"""
        if filename.lower().endswith('.pdf'):
            return DocumentParser.parse_pdf(content)
        elif filename.lower().endswith('.docx'):
            return DocumentParser.parse_docx(content)
        else:
            return content.decode('utf-8', errors='ignore')
