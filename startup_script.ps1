$wshShell = New-Object -ComObject WScript.Shell

# Start radio companion
Start-Process -FilePath "C:\Users\dell\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\GNU Radio\GNU Radio Companion.lnk"

# Wait for load up
Start-Sleep -Seconds 4

# Set focus to GNU window
[void]$wshShell.AppActivate( 'TrackSenseGNURadioWorkflow.grc - C:\Users\dell\Desktop' )

# Send F5 key (execute shortcut: generate graph)
$wshShell.SendKeys( '{F5}' )

# Wait for activation to succeed
Start-Sleep -Seconds 0.5

# Send F6 key (execute shortcut: execute graph)
$wshShell.SendKeys( '{F6}' )

# Wait for activation to succeed
Start-Sleep -Seconds 1

# Start standalone app
Start-Process -FilePath "C:\Users\dell\Desktop\main.exe"