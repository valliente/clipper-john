import os
import sys
import shutil
import subprocess

def validate_binary(binary_path):
    """
    Validates that the executable binary is functional.
    """
    try:
        if not os.path.exists(binary_path):
            return False
        cmd = [binary_path, "-version" if "ffmpeg" in binary_path.lower() else "--version"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate(timeout=3)
        return proc.returncode == 0
    except Exception:
        return False

def get_binary_path(binary_name):
    """
    Finds and validates the binary across PyInstaller MEIPASS, src/utils, local directory, or PATH.
    """
    if sys.platform == 'win32' and not binary_name.endswith('.exe'):
        binary_name += '.exe'
        
    candidates = []

    # 1. PyInstaller temp location
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, binary_name))

    # 2. src/utils location
    candidates.append(os.path.join(os.getcwd(), "src", "utils", binary_name))

    # 3. Local working dir
    candidates.append(os.path.join(os.getcwd(), binary_name))

    # 4. PATH lookup
    path_exe = shutil.which(binary_name)
    if path_exe:
        candidates.append(path_exe)

    for cand in candidates:
        if os.path.exists(cand):
            return cand
            
    return binary_name
