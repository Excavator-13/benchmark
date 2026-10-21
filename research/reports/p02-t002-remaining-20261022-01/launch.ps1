$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding
$OutputEncoding=[Console]::OutputEncoding
$env:PYTHONUTF8='1'
$runRoot='D:/research-runs/JODBSDFres/benchmark-r2-20261020-01'
Set-Location -LiteralPath $runRoot
$python='C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark/.venv-pinned/Scripts/python.exe'
$group=Join-Path $runRoot 'research/reports/p02-t002-remaining-20261022-01'
$status=@{status='running_region';started_at_utc=[DateTime]::UtcNow.ToString('o');wrapper_pid=$PID}
function Save-Group { $status | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $group 'queue.json') }
try {
 Save-Group
 & $python -B research/phases/P02/t002_remaining_batch.py run --data-name region --batch p02-t002-region-20261022-01
 if($LASTEXITCODE -ne 0){throw "region exited $LASTEXITCODE; r0 not scheduled"}
 $status.status='running_r0'; Save-Group
 & $python -B research/phases/P02/t002_remaining_batch.py run --data-name r0 --batch p02-t002-r0-20261022-01 --push-on-success
 if($LASTEXITCODE -ne 0){throw "r0 or publication exited $LASTEXITCODE"}
 $status.status='complete_and_pushed';$status.finished_at_utc=[DateTime]::UtcNow.ToString('o');Save-Group
} catch {
 $status.status='paused';$status.error=$_.Exception.Message;$status.finished_at_utc=[DateTime]::UtcNow.ToString('o');Save-Group
 throw
}

