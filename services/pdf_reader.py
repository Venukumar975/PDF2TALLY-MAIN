import pdfplumber
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%d-%b-%Y %I:%M:%S %p")

text_logger = logging.getLogger("FullTextDumper")
text_logger.propagate = False # Prevents the text from printing to the terminal console

user_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'PDF2TALLY')
logs_dir = os.path.join(user_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)

# 3. Attach a FileHandler targeting 'fulltext.log'
log_file_path = os.path.join(logs_dir, "fulltext.log")
file_handler = logging.FileHandler(log_file_path, mode="w", encoding="utf-8") # 'w' overwrites on every run
file_formatter = logging.Formatter(
    fmt="%(asctime)s - [RAW_TEXT_START]\n%(message)s\n[RAW_TEXT_END]\n",
    datefmt="%d-%b-%Y %I:%M:%S %p"
)
file_handler.setFormatter(file_formatter)
text_logger.addHandler(file_handler)
text_logger.setLevel(logging.INFO)


def extract_text(pdf_path):
    """
    Extracts the digital text layer from a PDF file.
    Dumps the full string extraction into 'fulltext.log' for diagnostic debugging.
    """

    full_text = ""
    
    try:

        with pdfplumber.open(pdf_path) as pdf:

                for page in pdf.pages:

                    page_text = page.extract_text()

                    if page_text:
                        full_text += page_text + "\n"
        if full_text.strip():
            text_logger.info(full_text)
            logging.info(f"💾 Captured raw content summary. Full text layer successfully dumped to '{log_file_path}'")
        else:
            logging.warning("⚠️ Text extraction returned empty strings. Nothing to dump to log file.")
        
        return full_text
    
    except Exception as e:
        logging.error(f"Failed to extract text from PDF path {pdf_path}. Error: {str(e)}")
        raise e
                        

