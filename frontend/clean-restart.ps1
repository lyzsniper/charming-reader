#!/usr/bin/env pwsh
# Clean restart script for frontend

Write-Host "=== Cleaning Frontend Build ===" -ForegroundColor Cyan

# Stop any running dev servers
Write-Host "Stopping dev server..." -ForegroundColor Yellow
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Clean cache and build artifacts
Write-Host "Cleaning cache and build artifacts..." -ForegroundColor Yellow
Remove-Item -Recurse -Force node_modules\.vite -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .vite -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Cleanup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Now run: pnpm run dev" -ForegroundColor Cyan
Write-Host "Then in browser: Press Ctrl+Shift+R to hard refresh" -ForegroundColor Cyan
