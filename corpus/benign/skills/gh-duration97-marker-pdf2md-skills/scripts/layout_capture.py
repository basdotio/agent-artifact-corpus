"""Capture positions from the same OCR pass, without changing installed packages."""
import json, os
from pathlib import Path

def install():
    from marker.converters.pdf import PdfConverter
    from run_diagnostics import stage
    # Table HTML already exists after full-page recognition in Marker 2.x.
    # Capture before/after its table processor to distinguish upstream processing
    # loss from Markdown rendering loss, without modifying that processor's data.
    from marker.processors.table import TableProcessor
    table_original = TableProcessor.__call__
    table_stages = []
    def tables(document):
        return [{'pdf_page': p.page_id + 1, 'blocks': [
            {'id': str(b.id), 'html': getattr(b, 'html', None), 'text': b.raw_text(document)}
            for b in p.current_children if not b.removed and b.block_type.name == 'Table']}
            for p in document.pages]
    def table_capture(self, document):
        stage('table_processing')
        before = tables(document)
        result = table_original(self, document)
        table_stages.append({'before_table_processing': before, 'after_table_processing': tables(document)})
        target = Path(os.environ['MARKER_LAYOUT_SIDECAR']).with_name('table_processing_evidence.json')
        target.write_text(json.dumps(table_stages, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    TableProcessor.__call__ = table_capture
    original = PdfConverter.build_document
    def capture(self, filepath):
        stage('recognition_and_document_processing')
        document = original(self, filepath)
        pages = []
        for page in document.pages:
            blocks = []
            for block in page.current_children:
                if block.removed or block.block_type.name in ('Span', 'Line'):
                    continue
                item = {'id': str(block.id), 'type': block.block_type.name,
                               'bbox': block.polygon.bbox, 'text': block.raw_text(document),
                               'ignored': block.ignore_for_output}
                if block.block_type.name == 'Table':
                    item['html'] = getattr(block, 'html', None)
                blocks.append(item)
            pages.append({'pdf_page': page.page_id + 1, 'bbox': page.polygon.bbox, 'blocks': blocks})
        Path(os.environ['MARKER_LAYOUT_SIDECAR']).write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
        stage('rendering')
        return document
    PdfConverter.build_document = capture
