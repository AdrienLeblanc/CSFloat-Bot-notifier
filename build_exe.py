import subprocess
import sys
import os

def install_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller non trouvé, installation...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_exe(script_name):
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        script_name
    ]
    print("Exécution de :", " ".join(cmd))
    subprocess.check_call(cmd)

if __name__ == "__main__":
    script = "csfloat_alerts.py"
    if not os.path.exists(script):
        print(f"Le fichier {script} est introuvable.")
        sys.exit(1)
    install_pyinstaller()
    build_exe(script)
    print("✅ Compilation terminée. L’exécutable est dans le dossier 'dist'.")
