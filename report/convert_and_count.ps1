param(
    [string]$DocxPath,
    [string]$PdfPath
)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $docxFull = (Resolve-Path $DocxPath).Path
    $pdfFull = [System.IO.Path]::GetFullPath($PdfPath)
    if (Test-Path $pdfFull) {
        Remove-Item $pdfFull -Force
    }
    $doc = $word.Documents.Open($docxFull)
    
    # Set 1-inch margins (72 points = 1 inch)
    $doc.PageSetup.TopMargin = 72
    $doc.PageSetup.BottomMargin = 72
    $doc.PageSetup.LeftMargin = 72
    $doc.PageSetup.RightMargin = 72

    # Set 11pt font across document content
    $doc.Content.Font.Size = 11

    # Export to PDF (17 = wdFormatPDF)
    $doc.SaveAs([ref]$pdfFull, [ref]17)

    # Compute page count
    $pages = $doc.ComputeStatistics(2) # 2 = wdStatisticPages
    Write-Host "PAGES:$pages"
    $doc.Close([ref]0)
}
finally {
    $word.Quit()
}
