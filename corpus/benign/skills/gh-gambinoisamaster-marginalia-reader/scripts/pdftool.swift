// Small PDF helper for journal.py, using macOS PDFKit. journal.py builds it on first use.
//
//   pdftool count <pdf>                           number of pages
//   pdftool heads <pdf> <first> <last>            one line per page: N<TAB>first text line<TAB>last text line
//   pdftool extract <pdf> <first> <last> <out>    write those pages to a new PDF
import Foundation
import PDFKit

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(1)
}

let args = CommandLine.arguments
guard args.count >= 3 else { fail("usage: pdftool count|heads|extract <pdf> ...") }
guard let doc = PDFDocument(url: URL(fileURLWithPath: args[2])) else { fail("couldn't open \(args[2])") }

func pages(_ a: String, _ b: String) -> ClosedRange<Int> {
    guard let first = Int(a), let last = Int(b), first >= 1, last >= first, last <= doc.pageCount else {
        fail("pages \(a)-\(b) are outside 1-\(doc.pageCount)")
    }
    return first...last
}

switch args[1] {
case "count":
    print(doc.pageCount)
case "heads" where args.count >= 5:
    for i in pages(args[3], args[4]) {
        let lines = (doc.page(at: i - 1)?.string ?? "")
            .split(whereSeparator: \.isNewline)
            .map { $0.replacingOccurrences(of: "\t", with: " ").trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        print("\(i)\t\(lines.first ?? "")\t\(lines.last ?? "")")
    }
case "extract" where args.count >= 6:
    let out = PDFDocument()
    for (k, i) in pages(args[3], args[4]).enumerated() {
        if let page = doc.page(at: i - 1) { out.insert(page, at: k) }
    }
    guard out.write(to: URL(fileURLWithPath: args[5])) else { fail("couldn't write \(args[5])") }
default:
    fail("usage: pdftool count|heads|extract <pdf> ...")
}
