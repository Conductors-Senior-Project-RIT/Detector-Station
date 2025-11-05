# Replace the content in quotes with the computer username.
$username = "username"
$onedrive = ""
$shortcutdir = "GNU Radio"

$wshShell = New-Object -ComObject WScript.Shell

# Start radio companion
$radiopath = "C:\Users\" + $username + "\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\" + $shortcutdir + "\GNU Radio Companion.lnk"
Start-Process -FilePath $radiopath

# Wait for load up
Start-Sleep -Seconds 12

# Set focus to GNU window
$windowname = "TrackSenseGNURadioWorkflow.grc - C:\Users\" + $username + "\Desktop\Tracksense"
[void]$wshShell.AppActivate( $windowname )

# Send F5 key (execute shortcut: generate graph)
$wshShell.SendKeys( '{F5}' )

# Wait for activation to succeed
Start-Sleep -Seconds 0.5

# Send F6 key (execute shortcut: execute graph)
$wshShell.SendKeys( '{F6}' )

# Wait for activation to succeed
Start-Sleep -Seconds 1

# Start standalone app
$dirpath = "C:\Users\" + $username + $onedrive + "\Desktop\Tracksense"
$apppath = "C:\Users\" + $username + $onedrive + "\Desktop\Tracksense\main.exe"
Start-Process -FilePath $apppath -WorkingDirectory $dirpath