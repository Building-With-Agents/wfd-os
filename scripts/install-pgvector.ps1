$src = "C:\Users\ritub\projects\wfd-os\scripts\pgvector-extracted"
$pgRoot = "C:\Program Files\PostgreSQL\18"

Write-Host "Installing pgvector 0.8.2 for PostgreSQL 18..."

Copy-Item "$src\lib\vector.dll" "$pgRoot\lib\" -Force
Write-Host "  Copied vector.dll"

Copy-Item "$src\share\extension\vector*" "$pgRoot\share\extension\" -Force
Write-Host "  Copied extension SQL files"

Write-Host "Verifying..."
if (Test-Path "$pgRoot\lib\vector.dll") {
    Write-Host "  vector.dll: OK"
} else {
    Write-Host "  vector.dll: MISSING!"
}
if (Test-Path "$pgRoot\share\extension\vector.control") {
    Write-Host "  vector.control: OK"
} else {
    Write-Host "  vector.control: MISSING!"
}

Write-Host "Restarting PostgreSQL..."
Restart-Service postgresql-x64-18
Write-Host "Done!"
