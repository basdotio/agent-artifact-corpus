# -*- coding: utf-8 -*-
"""
qa_inspector.py
大学通用实验报告 - PDF 质检与版面合规性检测器 (PDF QA & Layout Inspector)
使用 PyMuPDF 检查页数是否严格合规（B4横向3物理张/6页或A4标准），并可渲染高清多页预览图。
"""

import os
import sys
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import fitz # PyMuPDF
except ImportError:
    print("[Error] PyMuPDF (fitz) is not installed. Run 'pip install pymupdf'")
    sys.exit(1)

def inspect_pdf(pdf_path, output_dir=None, expected_sheets=3):
    if not os.path.exists(pdf_path):
        print(f"[Error] File not found: {pdf_path}")
        return False
        
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"==================================================")
    print(f" Universal Lab Report QA Inspector: {os.path.basename(pdf_path)}")
    print(f"==================================================")
    print(f"Total Physical Sheets: {total_pages} (Expected: {expected_sheets})")
    
    success = True
    if total_pages != expected_sheets:
        print(f"[FAIL] Physical sheet count mismatch! Got {total_pages}, expected {expected_sheets}.")
        success = False
    else:
        print(f"[PASS] Sheet count matches exact booklet standard: {total_pages} sheets.")
        
    for i, page in enumerate(doc):
        rect = page.rect
        w_pt = rect.width
        h_pt = rect.height
        print(f" Sheet {i+1}: Dimensions = {w_pt:.1f} pt x {h_pt:.1f} pt ({w_pt/72*25.4:.1f}mm x {h_pt/72*25.4:.1f}mm)")
        
        # 检查是否为 B4 横向 (约 1105.65 x 765.45)
        if abs(w_pt - 1105.65) < 15 and abs(h_pt - 765.45) < 15:
            print(f"         Status: [PASS] Strict B4 Landscape Booklet geometry.")
        else:
            print(f"         Status: [INFO] Custom/Standard dimensions.")
            
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            pix = page.get_pixmap(dpi=140)
            out_img = os.path.join(output_dir, f"sheet_{i+1}.png")
            pix.save(out_img)
            print(f"         Rendered QA preview: {out_img}")
            
    print(f"==================================================")
    return success

def main():
    parser = argparse.ArgumentParser(description="Universal Lab Report PDF QA Inspector")
    parser.add_argument("--pdf", required=True, help="Path to PDF report")
    parser.add_argument("--output-dir", help="Directory to save rendered sheet previews")
    parser.add_argument("--sheets", type=int, default=3, help="Expected physical sheets (default: 3 for B4 6-page)")
    args = parser.parse_args()
    
    passed = inspect_pdf(args.pdf, args.output_dir, args.sheets)
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
