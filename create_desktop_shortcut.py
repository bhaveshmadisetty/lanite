import os
import sys
import subprocess
import tempfile

def create_shortcut():
    """
    Creates a desktop shortcut (.lnk) for Lanite that runs via pythonw.exe.
    This hides the console window completely when launched.
    """
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        desktop, _ = winreg.QueryValueEx(key, "Desktop")
    except Exception:
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        
    shortcut_path = os.path.join(desktop, "Lanite.lnk")
    
    # Target executable and start directory
    pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    target_path = pythonw_path
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    main_py_path = os.path.join(project_dir, "main.py")
    icon_path = os.path.join(project_dir, "lanite_icon.ico")
    
    arguments = f'"{main_py_path}"'
    working_directory = project_dir
    
    q = chr(34)
    # VBScript to create the shortcut
    vbs_script = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_path}"
oLink.Arguments = {q}{q}{q}{main_py_path}{q}{q}{q}
oLink.WorkingDirectory = "{working_directory}"
oLink.Description = "Lanite - Offline Voice Dictation"
oLink.IconLocation = "{icon_path}"
oLink.Save
"""
    
    # Write VBScript to a temporary file and execute it
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False) as f:
            f.write(vbs_script)
            temp_vbs_path = f.name
            
        subprocess.run(["cscript.exe", "//nologo", temp_vbs_path], check=True)
        print(f"Successfully created Desktop shortcut at: {shortcut_path}")
        print("You can now double-click it to run Lanite in the background!")
    except Exception as e:
        print(f"Failed to create shortcut: {e}")
    finally:
        # Clean up temporary VBScript
        if os.path.exists(temp_vbs_path):
            os.remove(temp_vbs_path)

if __name__ == "__main__":
    create_shortcut()
