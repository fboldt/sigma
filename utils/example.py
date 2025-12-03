import sys

def python_version():
    v = sys.version_info
    print(f"Python version: {v.major}.{v.minor}.{v.micro}")
    print(f"Full version string: {sys.version}")

