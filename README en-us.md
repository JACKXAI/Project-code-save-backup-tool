Here's the translation of your text into English:

# Code Backup Tool

## Project Overview

The **Code Backup Tool** is a script designed for backing up project code. It can traverse a specified project directory, generate the directory structure of the project, and save the contents of all source code files in Markdown format to a specified backup file. This allows you to easily view the structure and code content of the project, making it convenient for sharing, reviewing, or archiving.

## Features

- **Project Directory Structure Generation**: Recursively traverse the project directory to generate a directory structure display similar to VSCode’s file tree, clearly presenting the hierarchical relationship of project files.
- **Source Code Backup**: Automatically collect source code files from common programming languages and embed their contents into the backup file for easy viewing.
- **Multiple Backup Management**: Automatically add numeric suffixes when backup files with the same name exist, preventing file overwriting and facilitating backup management.
- **High Robustness**: Equipped with exception handling mechanisms to manage files or directories without access permissions, ensuring stable program operation.
- **Progress Feedback**: Provides progress feedback when backing up a large number of files, allowing users to monitor backup progress.

## Environment Dependencies

- **Python 3.x**: It is recommended to use Python version 3.6 or above.

## Usage Instructions

1. **Run the Script**:
2. **Follow the Prompts**:

   - **Input Project Path**: Enter the absolute path of the project you want to back up when prompted.

     ```
     Enter project path (absolute path):
     > /path/to/your/project
     ```

   - **Input Save Path**: Enter the absolute path where the backup file will be saved. Pressing enter will default to saving in a folder named `backup_code` in the script's directory.

     ```
     Enter the path to save the backup file (absolute path, defaults to a folder named backup_code in the script directory):
     > /path/to/save/backup
     ```

3. **View Backup Results**:

   - The program will create a folder named after the project in the specified save path. If a folder with the same name exists, the program will automatically add a numeric suffix (e.g., `MyProject_1`, `MyProject_2`) to avoid overwriting the existing backup.
   - The backup file will be named in the format: `ProjectName_YYYYMMDD_HHMM.md`, containing the directory structure of the project and the contents of all source code files.

4. **Continue Operations**:

   - After the backup is complete, you can choose to continue backing up other projects or exit the program.

     ```
     Enter operation number:
     1. Continue backing up other projects
     0. Exit the program
     > 1
     ```

## Supported File Types

The program supports the following common programming language source code files by default:

- Python (`.py`)
- Java (`.java`)
- C/C++ (`.c`, `.cpp`, `.h`)
- C# (`.cs`)
- JavaScript/TypeScript (`.js`, `.jsx`, `.ts`, `.tsx`)
- Ruby (`.rb`)
- Go (`.go`)
- PHP (`.php`)
- Swift (`.swift`)
- Kotlin (`.kt`)
- Objective-C (`.m`, `.mm`)
- ...

You can extend the supported file types in the code as needed.

## Notes

- **Project Path**: Please ensure the project path you enter is valid and accessible, with permission to read the files within.
- **Save Path**: If the specified save path does not exist, the program will attempt to create it. If it cannot be created, please check the path's validity and permissions.
- **File Permissions**: When traversing directories, if any files or directories lack access permissions, the program will automatically skip them without affecting the backup process.
- **File Encoding**: The program uses UTF-8 encoding by default to read file contents. If it encounters encoding errors, it will attempt to use Latin-1 encoding.
- **Backup Management**: To prevent overwriting existing backups, the program will automatically add numeric suffixes when detecting projects with the same name. Please manage the backup folders to avoid consuming excessive storage space.

## Frequently Asked Questions

### 1. Why are some source code files not backed up?

Please check if the file extensions are in the list of supported file types. If you need to back up other types of files, please add the corresponding file extensions and language mappings in the `get_language_from_extension` function in the code.

### 2. What should I do if I encounter permission errors?

The program will automatically skip files or directories without access permissions. If you need to back up those contents, please run the program with a user that has sufficient permissions, or modify the permissions of the files/directories.

### 3. What should I do if the backup file is too large?

Since the program writes the contents of all source code files into the backup file, the generated Markdown file may be large for bigger projects. You can:

- Manually delete unnecessary parts (e.g., large data files, log files, etc.).
- Modify the program to backup only the directory structure or only specific file types.

## Contributing

Contributions are welcome! You can suggest improvements, report issues, or submit code enhancements by:

- Submitting an Issue or Pull Request to the project’s GitHub repository.

---

Thank you for using the **Code Backup Tool**! If you encounter any issues or have any suggestions during use, please feel free to contact me.
