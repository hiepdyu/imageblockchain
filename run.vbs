Set objShell = CreateObject("WScript.Shell") 
objShell.Run "cmd.exe /c streamlit run appv3.py", 0, False
