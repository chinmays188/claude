import csv
import io
import json
from abc import ABC, abstractmethod


class ParseError(Exception):
    pass


class DocumentParser(ABC):
    extensions: list[str]

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> str:
        """Return plain text extracted from the raw file bytes."""


class TextParser(DocumentParser):
    extensions = [".txt", ".md"]

    def parse(self, raw_bytes: bytes) -> str:
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ParseError(f"Could not decode text file as UTF-8: {exc}") from exc


class JsonParser(DocumentParser):
    extensions = [".json"]

    def parse(self, raw_bytes: bytes) -> str:
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParseError(f"Could not parse JSON: {exc}") from exc
        return json.dumps(data, indent=2)


class CsvParser(DocumentParser):
    extensions = [".csv"]

    def parse(self, raw_bytes: bytes) -> str:
        try:
            text = raw_bytes.decode("utf-8")
            reader = csv.reader(io.StringIO(text))
            rows = [", ".join(row) for row in reader]
        except UnicodeDecodeError as exc:
            raise ParseError(f"Could not decode CSV as UTF-8: {exc}") from exc
        return "\n".join(rows)


class PdfParser(DocumentParser):
    extensions = [".pdf"]

    def parse(self, raw_bytes: bytes) -> str:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
        except PdfReadError as exc:
            raise ParseError(f"Could not read PDF: {exc}") from exc
        return "\n\n".join(pages)


class DocxParser(DocumentParser):
    extensions = [".docx"]

    def parse(self, raw_bytes: bytes) -> str:
        import docx
        from docx.opc.exceptions import PackageNotFoundError

        try:
            document = docx.Document(io.BytesIO(raw_bytes))
        except PackageNotFoundError as exc:
            raise ParseError(f"Could not read DOCX: {exc}") from exc
        return "\n".join(p.text for p in document.paragraphs)


class ParserRegistry:
    def __init__(self, parsers: list[DocumentParser]):
        self._by_extension: dict[str, DocumentParser] = {}
        for parser in parsers:
            for ext in parser.extensions:
                self._by_extension[ext] = parser

    def get(self, filename: str) -> DocumentParser:
        ext = _extension_of(filename)
        if ext not in self._by_extension:
            raise ParseError(f"No parser registered for extension '{ext}'.")
        return self._by_extension[ext]

    def parse(self, filename: str, raw_bytes: bytes) -> str:
        return self.get(filename).parse(raw_bytes)


def default_parser_registry() -> ParserRegistry:
    return ParserRegistry([TextParser(), JsonParser(), CsvParser(), PdfParser(), DocxParser()])


def _extension_of(filename: str) -> str:
    idx = filename.rfind(".")
    if idx == -1:
        return ""
    return filename[idx:].lower()
