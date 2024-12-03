import os

def print_directory_structure(root_dir, indent_level=0):
    try:
        # List all files and directories in the root directory
        entries = os.listdir(root_dir)
        for entry in entries:
            entry_path = os.path.join(root_dir, entry)
            print("  " * indent_level + "|-- " + entry)
            # If the entry is a directory, recursively print its contents
            if os.path.isdir(entry_path):
                print_directory_structure(entry_path, indent_level + 1)
    except PermissionError:
        print("  " * indent_level + "|-- [Permission Denied]")

if __name__ == "__main__":
    # Get the current working directory
    current_root = os.getcwd()
    print(f"Root Directory: {current_root}")
    print_directory_structure(current_root)
