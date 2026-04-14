import importlib
import subprocess
import sys

packages = [
    "torch",
    "yfinance",
    "pandas",
    "numpy",
    "scikit-learn",
    "matplotlib",
    "shap",
    "jupyterlab",
    "ipykernel",
    "ta",
    "scipy",
    "tqdm",
]

print("Installation des packages...\n")
for pkg in packages:
    print(f"  Installing {pkg}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  OK {pkg}")
    else:
        print(f"  ERREUR {pkg}: {result.stderr.strip()}")

print("\nVerification des imports...")

# Map install name → importable name
import_names = {
    "torch":        "torch",
    "yfinance":     "yfinance",
    "pandas":       "pandas",
    "numpy":        "numpy",
    "scikit-learn": "sklearn",
    "matplotlib":   "matplotlib",
    "shap":         "shap",
    "scipy":        "scipy",
    "tqdm":         "tqdm",
}

all_ok = True
for install_name, import_name in import_names.items():
    try:
        mod = importlib.import_module(import_name)
        version = getattr(mod, "__version__", "OK")
        print(f"  {install_name} {version}")
    except ImportError as e:
        print(f"  MANQUANT {install_name}: {e}")
        all_ok = False

print()
if all_ok:
    print("Tous les packages sont installes et fonctionnels.")
else:
    print("Certains packages ont echoue — relance le script.")
