import os
import shutil

# Get the current working directory
current_dir = os.getcwd()

# Loop through all files and subdirectories in the current directory
for root, dirs, files in os.walk(current_dir):
    # Skip the root directory itself
    if root == current_dir:
        continue
    
    for file in files:
        # Construct the full file path
        file_path = os.path.join(root, file)
        
        # Move the file to the current directory
        if(file == "Thumbs.db"):
            os.remove(file_path)
        else:
            shutil.move(file_path, current_dir)

    # Once all files are moved, remove the empty folder
    if not os.listdir(root):  # Only remove if the directory is empty
        os.rmdir(root)

print("All files have been moved to the current folder.")