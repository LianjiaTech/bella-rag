from app.utils.docx2pdf_util import convert_docx_to_pdf_in_memory

file = "tests/resources/贝壳集团间接采购管理制度.docx"

def test_docx_convert():
    stream = open(file, "rb")
    pdf_stream = convert_docx_to_pdf_in_memory(stream)
    print(pdf_stream is not None)

test_docx_convert()