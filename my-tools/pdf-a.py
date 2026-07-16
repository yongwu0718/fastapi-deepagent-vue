import fitz  # pymupdf

pdf_path = r"F:\index_rag\knowledge-base\仿生腿爪机构的设计与验证——适用于多旋翼无人机的悬停与抓取功能，三区，if3.9(1).pdf"
output_path = r"F:\index_rag\knowledge-base\page_16.pdf"

doc = fitz.open(pdf_path)
page_num = 16
total = len(doc)

if page_num <= total:
    new_doc = fitz.open()                  # 新建空白 PDF
    new_doc.insert_pdf(doc, from_page=page_num-1, to_page=page_num-1)  # 插入第16页（索引15）
    new_doc.save(output_path)
    new_doc.close()
    print(f"第 {page_num} 页已保存为: {output_path}")
else:
    print(f"PDF 只有 {total} 页，无法提取第 {page_num} 页")
doc.close()