' Spine AI — hidden startup (no command windows)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Spine_AI"
WshShell.Run "D:\Spine_AI\Scripts\startup_spine.bat", 0, False
