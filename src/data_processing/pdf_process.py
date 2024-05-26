# Aqui primeiramente vamos tentar ler todo o arquivo pdf e retornar ele em formato de texto

import os
import fitz  # PyMuPDF

def pdf_to_text(pdf_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    text = ""
    
    # Iterate through each page
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text()

    return text

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Specify the path to the PDF file
pdf_path = os.path.join(script_dir, 'hemograma.pdf')  # Caminho absoluto para o arquivo PDF

# Convert PDF to text
pdf_text = pdf_to_text(pdf_path)

# Print the extracted text
print(pdf_text)
