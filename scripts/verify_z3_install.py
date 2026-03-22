import sys

try:
    import z3
    version = z3.get_version_string()
    print(f"Z3 version: {version}")
    print("Z3 OK")
    sys.exit(0)
except ImportError:
    print("Failed to import z3")
    sys.exit(1)
except Exception as e:
    print(f"Error checking z3: {e}")
    sys.exit(1)
