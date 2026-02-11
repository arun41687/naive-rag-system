import pdfplumber

pdf_path = 'LLM_Assignment.pdf'
with pdfplumber.open(pdf_path) as pdf:
    full_text = '\n'.join([page.extract_text() for page in pdf.pages])
    print(full_text)
