import os
import sys
import shutil

def get_binary_path(binary_name):
    """
    Finds the binary either in PyInstaller's temp folder, local directory, or PATH.
    """
    if sys.platform == 'win32' and not binary_name.endswith('.exe'):
        binary_name += '.exe'
        
    # Check PyInstaller bundled location
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        bundled_path = os.path.join(base_path, binary_name)
        if os.path.exists(bundled_path):
            return bundled_path
            
    # Check local workspace
    local_path = os.path.join(os.getcwd(), binary_name)
    if os.path.exists(local_path):
        return local_path
        
    # Check PATH
    path_executable = shutil.which(binary_name)
    if path_executable:
        return path_executable
        
    return binary_name # fallback
