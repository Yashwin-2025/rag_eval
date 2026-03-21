from docling.document_converter import DocumentConverter


def load_document_text(path: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(path)
    return result.document.export_to_markdown()