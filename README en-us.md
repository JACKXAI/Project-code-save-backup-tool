# Code Backup Tool

## Project Introduction

**Code Backup Tool** is a script used for backing up project code. It can traverse a specified project directory, generate the project's directory structure, and save the content of all source code files in Markdown format to a specified backup file. This way, you can easily view the project's structure and code content, making it convenient for sharing, reviewing, or archiving.

## Features

-   **Project Directory Structure Generation**: Recursively traverses the project directory to generate a directory structure display similar to the VSCode file tree, clearly and intuitively presenting the project's file hierarchy.
-   **Source Code Backup**: Automatically collects source code files of common programming languages and embeds their content into the backup file for easy viewing.
-   **Multiple Backup Management**: When a backup for a project with the same name exists, automatically adds a numeric suffix to prevent file overwriting, facilitating backup management.
-   **High Robustness**: Features an exception handling mechanism capable of handling files or directories without access permissions, ensuring stable program operation.
-   **Progress Indication**: Provides progress feedback when backing up a large number of files, allowing users to understand the backup progress.

## Environment Dependencies

-   **Python 3.x**: Python 3.6 or higher is recommended.

## Usage

1.  **Run the script**:
2.  **Follow the prompts**:

    -   **Enter Project Path**: Input the absolute path of the project you want to back up when prompted.

        ```
        Please enter the project path (absolute path):
        > /path/to/your/project
        ```

    -   **Enter Save Path**: Input the save path (absolute path) for the backup file. If you press Enter directly, it will default to saving in the `backup_code` folder within the script's directory.

        ```
        Please enter the path to save the backup file (absolute path, defaults to backup_code folder in script directory):
        > /path/to/save/backup
        ```

3.  **View Backup Results**:

    -   The program will create a folder named after the project in the specified save path. If a folder with the same name exists, the program will automatically add a numeric suffix (e.g., `MyProject_1`, `MyProject_2`) to avoid overwriting existing backups.
    -   The backup file naming format is: `ProjectName_YYYYMMDD_HHMM.md`, containing the project's directory structure and the content of all source code files.

4.  **Continue Operation**:

    -   After a backup is complete, you can choose to continue backing up other projects or exit the program.

        ```
        Please enter the operation number:
        1. Continue backing up another project
        0. Exit program
        > 1
        ```

## Supported File Types

The program supports the following common programming language source code files by default:

-   Python (`.py`)
-   Java (`.java`)
-   C/C++ (`.c`, `.cpp`, `.h`)
-   C# (`.cs`)
-   JavaScript/TypeScript (`.js`, `.jsx`, `.ts`, `.tsx`)
-   Ruby (`.rb`)
-   Go (`.go`)
-   PHP (`.php`)
-   Swift (`.swift`)
-   Kotlin (`.kt`)
-   Objective-C (`.m`, `.mm`)
-   ...

You can extend the supported file types in the code as needed.

## Precautions

-   **Project Path**: Ensure the entered project path is valid, accessible, and you have permission to read the files within it.
-   **Save Path**: If the specified save path does not exist, the program will attempt to create it. If creation fails, please check the path's validity and permissions.
-   **File Permissions**: When traversing directories, if files or directories without access permissions are encountered, the program will automatically skip them without affecting the backup process.
-   **File Encoding**: The program defaults to using UTF-8 encoding to read file content; if encoding errors occur, it will attempt to use Latin-1 encoding.
-   **Backup Management**: To prevent overwriting existing backups, the program automatically adds a numeric suffix when it detects a project with the same name. Please manage your backup folders to avoid consuming excessive storage space.

## FAQ

### 1. Why weren't some source code files backed up?

Please check if the file's extension is in the list of supported file types. If you need to back up other file types, please add the corresponding file extension and language mapping in the `get_language_from_extension` function in the code.

### 2. What to do if permission errors are encountered?

The program automatically skips files or directories it doesn't have permission to access. If you need to back up this content, please run the program as a user with sufficient permissions, or modify the file/directory permission settings.

### 3. The backup file is too large, how to handle it?

Since the program writes the content of all source code files into the backup file, the generated Markdown file can be large for bigger projects. You can:

-   Manually delete unnecessary parts (e.g., large data files, log files, etc.).
-   Modify the program to only back up the directory structure, or only specific file types.

## Contributing

Suggestions, issue reports, or code improvements are welcome. You can participate in the project through the following ways:

-   Submit an Issue or Pull Request to the project's GitHub repository.

---

Thank you for using the **Code Backup Tool**! If you have any questions or suggestions during use, feel free to contact me.

---

# Code Backup Tool Changelog

## Version 1.5.4 (2025-04-18)

### Performance Optimizations
-   **File Read Acceleration**: Implemented buffered reading for large files, reducing memory consumption by up to 80%.
-   **Enhanced Multi-threading**: Intelligently adjusts thread count and batch size based on file size.
-   **Batch Processing Mechanism**: Batch processing for small files reduces thread switching overhead, increasing processing speed by approximately 40%.
-   **Streamlined Processing**: Used `StringIO` instead of string concatenation, optimizing memory usage.
-   **ThreadPool Optimization**: Increased the default maximum thread count (CPU cores × 4) to better utilize I/O wait times.
-   **ZIP Compression Improvement**: Used a more efficient compression level, improving the compression ratio.
-   **Atomic File Operations**: Ensures the integrity of configuration and output files.

### .gitignore Filtering Optimizations
-   **Caching Mechanism**: Added path matching cache, reducing redundant calculations, improving .gitignore filtering speed by approximately 60%.
-   **Regex Pre-compilation**: Pre-compiled common patterns, reducing parsing overhead.
-   **Enhanced Pattern Handling**: Used `re.escape()` for safer handling of special characters.
-   **Exception Handling**: Added handling for invalid patterns, increasing robustness.

### User Experience Improvements
-   **Performance Statistics**: Added real-time performance metrics like file processing time and compression ratio.
-   **Optimized Progress Feedback**: Provides more detailed information during the backup process.
-   **Memory Usage Optimization**: Timely release of large object references, reducing peak memory consumption.
-   **Help Documentation Update**: Added explanations of performance optimizations for user awareness of new features.

### Code Optimizations
-   **Path Traversal Optimization**: Optimized the directory tree generation algorithm.
-   **Improved Type Hinting**: Enhanced code type annotations, improving maintainability.
-   **Enhanced Exception Handling**: More precise exception catching and handling.
-   **Configuration Management Optimization**: Added configuration cache to avoid frequent disk I/O.
-   **Improved Extensibility**: Optimized interface design for easier future feature expansion.

### Bug Fixes
-   **Large File Handling**: Fixed potential memory overflow issues when processing extremely large files.
-   **Character Encoding Handling**: Improved the handling mechanism for non-UTF-8 files.
-   **Path Compatibility**: Enhanced compatibility for path handling between Windows and Linux.
-   **Invalid .gitignore Rules**: Optimized the handling logic for incorrectly formatted .gitignore rules.

---

This version primarily focuses on performance optimization and stability enhancement. While maintaining the integrity of the original functionality, it significantly improves the program's execution speed and reduces resource consumption. For large project backups, performance improvements can reach 2-5x.
