// Render every page of a PDF with Apple PDFKit (the engine behind Preview, Quick Look, iOS and
// WhatsApp on Apple devices) to PNG, so we can catch viewer-specific breakage before sending.
// Usage: swift pdfkit_render.swift <in.pdf> <out_dir> [width_px]
import AppKit
import PDFKit

let args = CommandLine.arguments
guard args.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("usage: pdfkit_render.swift <in.pdf> <out_dir> [width]\n".data(using: .utf8)!)
    exit(2)
}
let outDir = args[2]
let width = args.count > 3 ? CGFloat(Double(args[3]) ?? 1280) : 1280
try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
for i in 0..<doc.pageCount {
    guard let page = doc.page(at: i) else { continue }
    let box = page.bounds(for: .mediaBox)
    let scale = width / box.width
    let size = NSSize(width: box.width * scale, height: box.height * scale)
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(size.width), pixelsHigh: Int(size.height),
                               bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    let ctx = NSGraphicsContext(bitmapImageRep: rep)!
    NSGraphicsContext.current = ctx
    let cg = ctx.cgContext
    cg.setFillColor(NSColor.white.cgColor)
    cg.fill(CGRect(origin: .zero, size: size))
    cg.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: cg)
    NSGraphicsContext.restoreGraphicsState()
    let png = rep.representation(using: .png, properties: [:])!
    let path = String(format: "%@/page-%02d.png", outDir, i + 1)
    try! png.write(to: URL(fileURLWithPath: path))
}
print("rendered \(doc.pageCount) pages with PDFKit")
