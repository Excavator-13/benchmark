$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = '1'
Set-Location -LiteralPath 'D:/research-runs/JODBSDFres/benchmark-r2-20261020-01'
& 'C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark/.venv-pinned/Scripts/python.exe' -B research/phases/P02/t002_r2_batch.py run --batch p02-t002-r2-20261020-02 --push-on-success
exit $LASTEXITCODE

