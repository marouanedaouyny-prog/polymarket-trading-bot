import subprocess
import sys

def run_pip(args):
    print(f"Running: pip {' '.join(args)}")
    subprocess.check_call([sys.executable, "-m", "pip"] + args)

def main():
    print("=== Environment Conflict Fixer ===")
    
    # List of packages known to cause conflicts in the current environment
    conflicting = [
        "gtts",
        "langchain-openai",
        "litellm",
        "seleniumbase",
        "pytest",
        "click",
        "openai",
        "websockets",
        "setuptools"
    ]
    
    print(f"Uninstalling conflicting packages: {', '.join(conflicting)}")
    try:
        run_pip(["uninstall", "-y"] + conflicting)
    except Exception as e:
        print(f"Warning during uninstall: {e}")

    print("\nReinstalling from hardened requirements.txt...")
    try:
        run_pip(["install", "-r", "requirements.txt"])
        print("\n✅ Environment fixed successfully!")
    except Exception as e:
        print(f"\n❌ Failed to reinstall: {e}")
        sys.exit(1)

    print("\nRunning final check...")
    subprocess.run([sys.executable, "-m", "pip", "check"])

if __name__ == "__main__":
    main()
