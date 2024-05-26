# Aqui nos vamos tentar extrair o valor de 1 só dado do pdf, com a formatação necessário no caso
# vamos tentar com a Hemoglobina

import os
import fitz  # PyMuPDF
import re

def pdf_to_text(pdf_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    text = ""
    
    # Iterate through each page
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text()

    return text

def extract_hemoglobin_value(text):
    # Regular expression pattern to find Hemoglobina value
    pattern = r'Hemoglobina[^0-9]*([\d,.]+)[^\d]*'
    
    # Search for the pattern in the text
    match = re.search(pattern, text)
    
    # If a match is found, return the value, otherwise return None
    if match:
        return match.group(1)
    else:
        return None

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Specify the path to the PDF file
pdf_path = os.path.join(script_dir, 'hemograma.pdf')  # Caminho absoluto para o arquivo PDF

# Convert PDF to text
pdf_text = pdf_to_text(pdf_path)

# Extract Hemoglobina value
hemoglobin_value = extract_hemoglobin_value(pdf_text)

# Print the extracted Hemoglobina value
print(hemoglobin_value)
