import streamlit as st
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor

# ---------------------------
# 목차 PDF 생성 함수
# ---------------------------
def create_toc_page(entries):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 제목 스타일링
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(HexColor("#1F4E79"))
    c.drawString(72, height - 72, "목차 (Table of Contents)")

    # 목차 항목 스타일링
    c.setFont("Helvetica", 13)
    c.setFillColor(HexColor("#333333"))
    y = height - 110
    link_positions = []

    for i, entry in enumerate(entries, start=1):
        line = f"{i}. {entry['title']} ...... p. {entry['start_page']}"
        c.drawString(80, y, line)
        link_positions.append(y)
        y -= 22  # 줄 간격
        if y < 72:
            c.showPage()
            y = height - 72

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue(), link_positions, width

# ---------------------------
# PDF 병합 + 미리보기
# ---------------------------
def merge_pdfs_with_toc(uploaded_files, custom_titles):
    pdf_infos = []
    for uf in uploaded_files:
        reader = PdfReader(uf)
        num_pages = len(reader.pages)
        pdf_infos.append({
            "name": uf.name,
            "reader": reader,
            "num_pages": num_pages,
            "custom_title": custom_titles.get(uf.name, uf.name)
        })

    # 시작 페이지 계산
    entries = []
    current_page = 1
    for info in pdf_infos:
        start_page = current_page + 1
        entries.append({
            "title": info["custom_title"],
            "start_page": start_page
        })
        current_page += info["num_pages"]

    # 목차 PDF 생성
    toc_pdf_bytes, link_positions, toc_page_width = create_toc_page(entries)
    toc_reader = PdfReader(BytesIO(toc_pdf_bytes))

    # PDF 병합
    writer = PdfWriter()
    for page in toc_reader.pages:
        writer.add_page(page)

    start_page_indices = []
    for info in pdf_infos:
        start_index = len(writer.pages)
        start_page_indices.append(start_index)
        for page in info["reader"].pages:
            writer.add_page(page)

    # 북마크 추가
    for info, page_index in zip(pdf_infos, start_page_indices):
        writer.add_outline_item(info["custom_title"], page_index)

    # 목차 클릭 링크 추가
    for i, (entry, y) in enumerate(zip(entries, link_positions)):
        target_page_index = start_page_indices[i]
        rect = (70, y - 2, toc_page_width - 70, y + 12)
        annotation = Link(rect=rect, target_page_index=target_page_index)
        writer.add_annotation(page_number=0, annotation=annotation)

    # 결과를 BytesIO 반환
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.getvalue()

# ---------------------------
# Streamlit UI
# ---------------------------
def main():
    st.set_page_config(
        page_title="Styled PDF Merger",
        page_icon="📄",
        layout="centered"
    )
    
    st.title("Styled PDF Merger")
    st.write("여러 PDF를 병합하고 클릭 가능한 스타일 목차를 생성하며, 업로드한 PDF를 미리 볼 수 있습니다.")

    uploaded_files = st.file_uploader(
        "PDF 파일을 여러 개 선택하세요.",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.write("업로드된 파일:")
        for uf in uploaded_files:
            st.write(f"- {uf.name}")

        # 커스텀 제목 입력
        st.write("각 PDF의 목차 제목을 입력하세요 (기본값 = 파일명)")
        custom_titles = {}
        for uf in uploaded_files:
            title = st.text_input(f"{uf.name}의 목차 제목", value=uf.name)
            custom_titles[uf.name] = title

        # PDF 미리보기
        st.write("업로드된 PDF 미리보기:")
        for uf in uploaded_files:
            st.write(f"**{uf.name}**")
            st.download_button(
                label="다운로드 미리보기 PDF",
                data=uf.read(),
                file_name=uf.name,
                mime="application/pdf"
            )
            uf.seek(0)  # 다시 읽기 위해 파일 포인터 초기화

        if st.button("병합 PDF 생성"):
            merged_pdf = merge_pdfs_with_toc(uploaded_files, custom_titles)
            st.success("병합 완료! 목차 클릭과 스타일링이 적용되었습니다.")
            st.download_button(
                label="병합된 PDF 다운로드",
                data=merged_pdf,
                file_name="merged_styled_toc.pdf",
                mime="application/pdf",
            )

if __name__ == "__main__":
    main()
