param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8000
)

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    Write-Host "Starting backend on http://$BindHost`:$Port"
    Write-Host "If you have set GEMINI_API_KEY in your environment, the Gemini planner will be used."
    uvicorn backend.server:app --host $BindHost --port $Port --reload
}
finally {
    Pop-Location
}
