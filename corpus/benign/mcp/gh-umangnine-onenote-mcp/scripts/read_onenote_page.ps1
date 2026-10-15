<#
.SYNOPSIS
    Reads and outputs content from a Microsoft OneNote page via COM Automation.

.DESCRIPTION
    Connects to the running OneNote desktop application in STA mode, extracts the
    specified page's XML DOM, and converts it into formatted console text or Markdown.

.PARAMETER Notebook
    The notebook name (e.g., 'Notes-2026').

.PARAMETER Section
    The section name (e.g., 'Update-Notes-26').

.PARAMETER PageTitle
    Optional title of the page to read. If omitted, lists available pages.

.PARAMETER AsMarkdown
    Switch to output clean Markdown instead of plain text.

.EXAMPLE
    .\read_onenote_page.ps1 -Notebook "Notes-2026" -Section "Update-Notes-26"
    .\read_onenote_page.ps1 -Notebook "Notes-2026" -Section "Update-Notes-26" -PageTitle "Wednesday, 30 September, 2026" -AsMarkdown
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)]
    [string]$Notebook,

    [Parameter(Mandatory = $true)]
    [string]$Section,

    [Parameter(Mandatory = $false)]
    [string]$PageTitle,

    [switch]$AsMarkdown
)

$ErrorActionPreference = 'Stop'

# 0. Force UTF-8 Output Encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 1. Enforce STA (Single-Threaded Apartment) mode
$aptState = [System.Threading.Thread]::CurrentThread.GetApartmentState()
if ($aptState -ne "STA") {
    $sysRoot = if ($env:SystemRoot) { $env:SystemRoot } else { "C:\Windows" }
    $ps51 = Join-Path $sysRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    if (Test-Path $ps51) {
        & $ps51 -STA -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath @args
        exit $LASTEXITCODE
    }
}

$onenote = $null
try {
    try {
        $onenote = New-Object -ComObject OneNote.Application
    } catch {
        $msg = $_.Exception.Message
        if ($msg -match "0x80040154") {
            Write-Error "Microsoft OneNote Desktop is NOT installed. Note: The Store app 'OneNote for Windows 10' does not support COM."
        } elseif ($msg -match "0x80080005") {
            Write-Error "OneNote COM server execution failed. Check if a modal dialog or password prompt is open in OneNote Desktop."
        } else {
            Write-Error "Could not initialize OneNote COM Application: $msg"
        }
        exit 1
    }

    # 1. Fetch Section Hierarchy (Level 3: Sections included)
    $hXml = ""
    try {
        $onenote.GetHierarchy("", 3, [ref]$hXml)
    } catch {
        Write-Error "Failed to retrieve OneNote hierarchy: $_"
        exit 1
    }

    $doc = [xml]$hXml
    $nsMgr = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
    $nsMgr.AddNamespace("one", "http://schemas.microsoft.com/office/onenote/2013/onenote")

    # Locate Notebook
    $nbNode = $doc.SelectSingleNode("//one:Notebook[translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '$($Notebook.ToLower())']", $nsMgr)
    if (-not $nbNode) {
        Write-Error "Notebook '$Notebook' not found. Available notebooks: $($doc.SelectNodes('//one:Notebook/@name').Value -join ', ')"
        exit 1
    }

    # Locate Section
    $secNode = $nbNode.SelectSingleNode(".//one:Section[translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '$($Section.ToLower())']", $nsMgr)
    if (-not $secNode) {
        Write-Error "Section '$Section' not found in notebook '$Notebook'."
        exit 1
    }

    # 2. Fetch pages specifically for this section (targeted query - fast)
    $secPagesXml = ""
    $onenote.GetHierarchy($secNode.ID, 4, [ref]$secPagesXml)
    $secDoc = [xml]$secPagesXml
    $pNsMgr = New-Object System.Xml.XmlNamespaceManager($secDoc.NameTable)
    $pNsMgr.AddNamespace("one", "http://schemas.microsoft.com/office/onenote/2013/onenote")
    $pages = $secDoc.SelectNodes("//one:Page", $pNsMgr)

    # If no specific page requested, list all pages in this section
    if ([string]::IsNullOrWhiteSpace($PageTitle)) {
        Write-Host "`n=== Pages in [$Notebook / $Section] ===" -ForegroundColor Cyan
        foreach ($p in $pages) {
            Write-Host "• $($p.name) (ID: $($p.ID))"
        }
        Write-Host "`nPass -PageTitle '<Title>' to read page content."
        exit 0
    }

    # Find requested page
    $targetPage = $null
    foreach ($p in $pages) {
        if ($p.name -like "*$PageTitle*") {
            $targetPage = $p
            break
        }
    }

    if (-not $targetPage) {
        Write-Error "Page '$PageTitle' not found in section '$Section'."
        exit 1
    }

    # 3. Retrieve Page Content XML
    $pageContentXml = ""
    $onenote.GetPageContent($targetPage.ID, [ref]$pageContentXml, 0)
    $pageDoc = [xml]$pageContentXml
    $pNs = New-Object System.Xml.XmlNamespaceManager($pageDoc.NameTable)
    $pNs.AddNamespace("one", "http://schemas.microsoft.com/office/onenote/2013/onenote")

    $titleNode = $pageDoc.SelectSingleNode("//one:Title//one:T", $pNs)
    $title = if ($titleNode) { $titleNode.InnerText } else { $targetPage.name }

    if ($AsMarkdown) {
        Write-Output "# $title`n"
    } else {
        Write-Host "`n==================================================" -ForegroundColor Yellow
        Write-Host " PAGE: $title" -ForegroundColor Yellow
        Write-Host "==================================================`n" -ForegroundColor Yellow
    }

    # Function to recursively render Outline Elements with proper indentation
    function Render-OEChildren($containerNode, [int]$indent = 0) {
        $childOEs = $containerNode.SelectNodes("one:OE", $pNs)
        foreach ($oe in $childOEs) {
            $tNode = $oe.SelectSingleNode("one:T", $pNs)
            $tableNode = $oe.SelectSingleNode("one:Table", $pNs)
            $isBullet = $oe.SelectSingleNode("one:List/one:Bullet", $pNs) -ne $null
            $isNumber = $oe.SelectSingleNode("one:List/one:Number", $pNs) -ne $null

            $prefix = "  " * $indent

            if ($tNode) {
                $raw = $tNode.InnerText
                $clean = [System.Text.RegularExpressions.Regex]::Replace($raw, "<[^>]+>", "")
                $clean = [System.Net.WebUtility]::HtmlDecode($clean).Trim()

                if (-not [string]::IsNullOrWhiteSpace($clean)) {
                    if ($AsMarkdown) {
                        if ($isBullet) {
                            Write-Output "$prefix- $clean"
                        } elseif ($isNumber) {
                            Write-Output "$prefix1. $clean"
                        } else {
                            Write-Output "`n$clean"
                        }
                    } else {
                        if ($isBullet) {
                            Write-Host "$prefix• $clean"
                        } elseif ($isNumber) {
                            Write-Host "$prefix1. $clean"
                        } else {
                            Write-Host "$prefix$clean"
                        }
                    }
                }
            }

            if ($tableNode) {
                $rows = $tableNode.SelectNodes("one:Row", $pNs)
                foreach ($row in $rows) {
                    $cells = $row.SelectNodes("one:Cell", $pNs)
                    $cellTexts = @()
                    foreach ($cell in $cells) {
                        $cTextNode = $cell.SelectSingleNode(".//one:T", $pNs)
                        $cText = if ($cTextNode) {
                            $cClean = [System.Text.RegularExpressions.Regex]::Replace($cTextNode.InnerText, "<[^>]+>", "")
                            [System.Net.WebUtility]::HtmlDecode($cClean).Trim()
                        } else { "" }
                        $cellTexts += $cText
                    }
                    if ($AsMarkdown) {
                        Write-Output "| $($cellTexts -join ' | ') |"
                    } else {
                        Write-Host "[$($cellTexts -join ' | ')]"
                    }
                }
                if ($AsMarkdown) { Write-Output "" }
            }

            # Recurse for nested child OEChildren (true sub-bullets)
            $nestedChildren = $oe.SelectSingleNode("one:OEChildren", $pNs)
            if ($nestedChildren) {
                Render-OEChildren $nestedChildren ($indent + 1)
            }
        }
    }

    $outlines = $pageDoc.SelectNodes("//one:Outline/one:OEChildren", $pNs)
    foreach ($outlineContainer in $outlines) {
        Render-OEChildren $outlineContainer 0
    }
} finally {
    if ($onenote) {
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($onenote) | Out-Null
        [System.GC]::Collect()
        [System.GC]::WaitForPendingFinalizers()
    }
}
