# powershell -NoProfile -ExecutionPolicy Bypass -File render.ps1 <deck.pptx> <out> [pdf|png]
# PowerPoint is the Windows renderer (COM). pdf → <out> is the PDF file; png → <out> is a folder, one PNG per slide
# (the counterpart of render.applescript). The deck opens without a window, is closed afterwards, and PowerPoint is
# quit only when WE launched it (no presentation was open before): the user may have unsaved decks open.
param(
  [Parameter(Mandatory = $true)][string]$Deck,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$Mode = "pdf"
)
$ErrorActionPreference = "Stop"
$code = 0
$app = $null; $pres = $null; $launched = $false
try {
  $Deck = (Resolve-Path $Deck).Path   # COM wants absolute paths; a relative one resolves against PowerPoint's cwd
  $Out = [System.IO.Path]::GetFullPath($Out)
  $app = New-Object -ComObject PowerPoint.Application   # attaches to a running instance or starts one
  $launched = ($app.Presentations.Count -eq 0)
  # Open(FileName, ReadOnly, Untitled, WithWindow): msoTrue = -1, msoFalse = 0. No window → nothing flashes on screen.
  $pres = $app.Presentations.Open($Deck, -1, 0, 0)
  if ($Mode -eq "png") {
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    $pres.Export($Out, "PNG", 1920, 1080)   # Slide1.PNG, Slide2.PNG, …
  } else {
    $pres.SaveAs($Out, 32)                  # ppSaveAsPDF
  }
} catch {
  [Console]::Error.WriteLine("render.ps1: $($_.Exception.Message)")
  $code = 1
} finally {
  if ($pres) { try { $pres.Close() } catch { } }
  if ($app -and $launched -and $app.Presentations.Count -eq 0) { try { $app.Quit() } catch { } }
}
exit $code
