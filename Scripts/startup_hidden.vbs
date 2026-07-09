' Spine AI — hidden startup (launches pythonw directly, no cmd windows)
Set WshShell = CreateObject("WScript.Shell")
root = "D:\Spine_AI"
WshShell.CurrentDirectory = root

' Start Ollama brain silently
ollama = CreateObject("WScript.Shell").ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Ollama\Ollama.exe"
Set fso = CreateObject("Scripting.FileSystemObject")
If fso.FileExists(ollama) Then
    WshShell.Run """" & ollama & """", 0, False
End If

' Start Spine orb + voice
py = root & "\.venv\Scripts\pythonw.exe"
main = root & "\spine\main.py"
WshShell.Run """" & py & """ """ & main & """ --visual --startup", 0, False
