
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path "models\te" | Out-Null

$base = "https://huggingface.co/parismitaglobalsolutions/indicconformer-sherpa-onnx/resolve/main"

$downloads = @(
    @{ Url = "$base/tokens.txt"; Path = "models\tokens.txt" },
    @{ Url = "$base/te/model.int8.onnx"; Path = "models\te\model.int8.onnx" }
)

foreach ($item in $downloads) {
    if (-not (Test-Path $item.Path)) {
        Write-Host "Downloading $($item.Path)..."
        Invoke-WebRequest -Uri $item.Url -OutFile $item.Path
    } else {
        Write-Host "Already downloaded: $($item.Path)"
    }
}

Write-Host "Telugu model download step finished."
