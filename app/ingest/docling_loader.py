from functools import lru_cache


@lru_cache(maxsize=1)
def _get_converter():
    # Imported lazily: docling pulls in torch/transformers, which cost minutes of startup on
    # machines where only chat/dashboard is used. Only /ingest pays this, once.
    import sys

    if "transformers" in sys.modules and sys.modules["transformers"] is None:
        del sys.modules["transformers"]  # lift the startup block set in app/__init__.py
    from docling.document_converter import DocumentConverter

    return DocumentConverter()


def load_document_text(path: str) -> str:
    result = _get_converter().convert(path)
    return result.document.export_to_markdown()
