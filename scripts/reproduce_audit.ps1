param([switch]$KeepRunning)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
$out = Join-Path $root 'output\audit-reproduction'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$legacy = & git show '7929c0c:backend/app/schemas/survey.py'
if ($LASTEXITCODE -ne 0) { throw 'The full Git history with revision 7929c0c is required. No database was changed.' }
[IO.File]::WriteAllText((Join-Path $out 'legacy-survey-schema.py'), ($legacy -join "`n"), [Text.UTF8Encoding]::new($false))
$compose = @('compose', '-p', 'survey-audit-evidence', '-f', 'docker-compose.audit.yml')
$log = Join-Path $out 'commands.log'
[IO.File]::WriteAllText($log, "Audit started $([DateTime]::UtcNow.ToString('o'))`n", [Text.UTF8Encoding]::new($false))
function Invoke-AuditDocker([string[]]$Arguments) {
    $ErrorActionPreference = 'Continue'
    [IO.File]::AppendAllText($log, ('docker ' + ($compose + $Arguments -join ' ') + "`n"))
    $lines = & docker @compose @Arguments 2>&1
    $code = $LASTEXITCODE
    $lines | ForEach-Object { [IO.File]::AppendAllText($log, ($_.ToString() + "`n")) }
    if ($code -ne 0) { throw "Audit command failed (exit $code). See output/audit-reproduction/commands.log." }
    $lines | ForEach-Object { Write-Host $_ }
}
try {
    Invoke-AuditDocker -Arguments @('up', '-d', '--build', '--wait', 'db', 'backend')
    Invoke-AuditDocker -Arguments @('exec', '-T', 'backend', 'python', '-m', 'tests.supervisor_audit')
    Invoke-AuditDocker -Arguments @('exec', '-T', 'backend', 'python', '-m', 'unittest', 'tests.test_translation', '-v')
    Invoke-AuditDocker -Arguments @('exec', '-T', 'backend', 'python', '-m', 'tests.http_audit')
    Invoke-AuditDocker -Arguments @('exec', '-T', 'backend', 'python', '-m', 'tests.repeat_load')
    $restore = 'survey_audit_restore_' + [DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
    Invoke-AuditDocker -Arguments @('exec', '-T', 'db', 'pg_dump', '-U', 'survey_user', '-Fc', '-f', '/tmp/audit.dump', 'survey_audit_reproduce')
    Invoke-AuditDocker -Arguments @('exec', '-T', 'db', 'createdb', '-U', 'survey_user', $restore)
    Invoke-AuditDocker -Arguments @('exec', '-T', 'db', 'pg_restore', '-U', 'survey_user', '--exit-on-error', '-d', $restore, '/tmp/audit.dump')
    Invoke-AuditDocker -Arguments @('exec', '-T', '-e', 'AUDIT_SOURCE_DATABASE=survey_audit_reproduce', '-e', "AUDIT_RESTORE_DATABASE=$restore", 'backend', 'python', '-m', 'tests.verify_restore')
    Invoke-AuditDocker -Arguments @('run', '--rm', '--build', 'bot-tests')
    Invoke-AuditDocker -Arguments @('run', '--rm', '--build', 'frontend-tests')
    [IO.File]::AppendAllText($log, "Audit completed $([DateTime]::UtcNow.ToString('o'))`n")
    Write-Host 'Audit completed. Evidence: output/audit-reproduction. Production data and Telegram were not used.'
} finally {
    if (-not $KeepRunning) { & docker @compose down }
}
