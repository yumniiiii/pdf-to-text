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

    # 제목 스타일링: 큰 글씨, 파란색
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(HexColor("#1F4E79"))  # 파란색
    c.drawString(72, height - 72, "목차 (Table of Contents)")

    # 목차 항목 스타일링: 13pt, 회색
    c.setFont("Helvetica", 13)
    c.setFillColor(HexColor("#333333"))

    y = height - 110
    link_positions = []

    for i, entry in enumerate(entries, start=1):
        line = f"{i}. {entry['title']} ...... p. {entry['start_page']}"
        c.drawString(80, y, line)
        link_positions.append(y)
        y -= 22  # 줄 간격 확대
        if y < 72:
            c.showPage()
            y = height - 72  # 다음 페이지 시작점

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue(), link_positions, width

# ---------------------------
# PDF 병합 함수
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

    # 시작 페이지 계산 (TOC = 1페이지)
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

    # ---------------------------
    # 병합된 PDF 모든 페이지에 페이지 번호 추가
    # ---------------------------
    for i, page in enumerate(writer.pages):
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#555555"))
        c.drawRightString(width - 72, 20, f"- {i + 1} -")
        c.save()
        packet.seek(0)

        # 기존 페이지 위에 덮어쓰기
        number_pdf = PdfReader(packet)
        page.merge_page(number_pdf.pages[0])

    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.getvalue()

# ---------------------------
# Streamlit UI
# ---------------------------
def main():
    st.title("PDF 병합 + 클릭 가능한 목차 + 페이지 번호")
    st.write("여러 PDF를 업로드하면 하나로 병합하고, 목차와 페이지 번호를 자동 생성합니다.")

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

        if st.button("병합 PDF 생성"):
            merged_pdf = merge_pdfs_with_toc(uploaded_files, custom_titles)
            st.success("병합 완료! 목차 클릭과 페이지 번호가 추가되었습니다.")
            st.download_button(
                label="병합된 PDF 다운로드",
                data=merged_pdf,
                file_name="merged_with_toc_and_page_numbers.pdf",
                mime="application/pdf",
            )

if __name__ == "__main__":
    main()
