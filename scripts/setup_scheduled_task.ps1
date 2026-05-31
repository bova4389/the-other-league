# setup_scheduled_task.ps1
# Run this ONCE to register the Tuesday update task in Windows Task Scheduler.
# After that, the task runs automatically every Tuesday at 9am ET.
# If the PC is off at 9am, it runs the next time the PC is turned on.
#
# Usage (run from PowerShell as administrator, or right-click → Run with PowerShell):
#   powershell -ExecutionPolicy Bypass -File "scripts\setup_scheduled_task.ps1"

$taskName   = "TOL-Tuesday-H2H-Update"
$batchFile  = Join-Path $PSScriptRoot "run_tuesday_update.bat"

# Remove existing task if it exists (clean re-register)
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed existing task '$taskName'."
}

# Action: run the batch file in a minimized window
$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$batchFile`""

# Trigger: every Tuesday at 9:00 AM
$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Tuesday `
    -At "9:00AM"

# Settings:
#   -StartWhenAvailable  → if PC was off at 9am, run as soon as it next boots
#   -RunOnlyIfNetworkAvailable → don't run without internet (Sleeper API needs it)
#   -ExecutionTimeLimit PT10M → kill if still running after 10 min (should take <30 sec)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

# Register the task for the current user (no admin rights needed after this)
Register-ScheduledTask `
    -TaskName $taskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force

Write-Host ""
Write-Host "✓ Task '$taskName' registered successfully."
Write-Host ""
Write-Host "It will run every Tuesday at 9:00 AM."
Write-Host "If your PC is off at 9am, it runs the next time you turn it on."
Write-Host ""
Write-Host "Output logs: scripts\tuesday_update.log (in your repo folder)"
Write-Host ""
Write-Host "To run it manually right now:"
Write-Host "  Start-ScheduledTask -TaskName '$taskName'"
Write-Host ""
Write-Host "To check it in Task Scheduler: open Task Scheduler → Task Scheduler Library"
