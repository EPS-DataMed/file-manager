# Aqui tentaremos capturar mais de 2 valores ao mesmo tempo
# Rodando ok, com arquivo PDF do laboratório da Unimed

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

def extract_blood_values(text):
    # Regular expression patterns to find values of Hemoglobina, Hematócrito, and Eritrócitos
    pattern_hemoglobin = r'Hemoglobina[^0-9]*([\d,.]+)[^\d]*'
    pattern_hematocrit = r'Hematócrito[^0-9]*([\d,.]+)[^\d]*'
    pattern_eritrocitos = r'Eritrócitos[^0-9]*([\d,.]+)[^\d]*'
    
    # Search for the patterns in the text
    match_hemoglobin = re.search(pattern_hemoglobin, text)
    match_hematocrit = re.search(pattern_hematocrit, text)
    match_eritrocitos = re.search(pattern_eritrocitos, text)
    
    # If matches are found, return the values, otherwise return None
    if match_hemoglobin and match_hematocrit and match_eritrocitos:
        hemoglobin_value = match_hemoglobin.group(1)
        hematocrit_value = match_hematocrit.group(1)
        eritrocitos_value = match_eritrocitos.group(1)
        return hemoglobin_value, hematocrit_value, eritrocitos_value
    else:
        return None, None, None

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Specify the path to the PDF file
pdf_path = os.path.join(script_dir, 'hemograma.pdf')  # Caminho absoluto para o arquivo PDF

# Convert PDF to text
pdf_text = pdf_to_text(pdf_path)

# Extract values
hemoglobin_value, hematocrit_value, eritrocitos_value = extract_blood_values(pdf_text)

# Print the extracted values
print("Valor da Hemoglobina:", hemoglobin_value)
print("Valor do Hematócrito:", hematocrit_value)
print("Valor dos Eritrócitos (Hemácias):", eritrocitos_value)
