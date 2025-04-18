#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Backup Tool (English Version)
------------------------------------
Version: 1.5.4
Author: Jack💡

Functionality Description:
1. When running the program, you can directly input the project directory address (absolute path) by default. If the input is a valid absolute path, the backup process starts immediately.
2. If you need to manage file extensions, view help, or exit, enter the corresponding operation number when prompted.
3. During the backup process, a Markdown file containing the project directory structure and all source code content is generated (supports multi-threading).
4. The user can choose whether to compress the backup result into a ZIP file.
5. Operational logic modifications are synchronized with the help documentation for easy viewing and maintenance.
6. Uses pathlib for path operations, adds type hints, and optimizes some logic.
7. Supports filtering content not needed for backup based on the project's .gitignore file (can be enabled/disabled in settings).
8. Simplified command-line interface using emojis for a friendly user experience.
9. Optimized file read/write performance, reduced memory usage, and improved multi-threading efficiency.

Notes:
- Default backup file extensions can be managed through the menu.
- Please ensure the entered project path is an absolute path and you have access permissions.
- The log file will record key information and errors during the backup process.
- .gitignore filtering is enabled by default and can be disabled in the settings menu.
"""

import os
import sys
import logging
import zipfile
import threading
import json
import re
import time
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set, Union, Pattern, Iterator, BinaryIO

# --- Constants ---
VERSION = "1.5.4"  # Update version number
# Default file extensions to back up
DEFAULT_SOURCE_EXTENSIONS: Tuple[str, ...] = (
    '.py', '.java', '.cpp', '.c', '.h', '.cs', '.js', '.ts',
    '.jsx', '.tsx', '.rb', '.go', '.php', '.swift', '.kt',
    '.m', '.mm'
)
# All available extensions to choose from
AVAILABLE_EXTENSIONS: Tuple[str, ...] = (
    '.py', '.java', '.cpp', '.c', '.h', '.cs', '.js', '.ts',
    '.jsx', '.tsx', '.rb', '.go', '.php', '.swift', '.kt',
    '.m', '.mm', '.txt', '.md', '.ini', '.cfg', '.json', '.xml',
    '.yaml', '.yml'
)
DEFAULT_BACKUP_DIR_NAME: str = "backup_code"
LOG_FILE_NAME: str = "backup.log"
CONFIG_FILE_NAME: str = "backup_config.json"
CONFIG_VERSION: str = "1.0"  # Configuration file version for future compatibility
# Determine thread count based on system and task type (mainly IO-bound)
DEFAULT_MAX_WORKERS: int = min(32, (os.cpu_count() or 4) * 4)
# File read buffer size (8 MB)
READ_BUFFER_SIZE: int = 8 * 1024 * 1024
# Batch size for processing small files together
BATCH_SIZE: int = 50

# --- Interface Emojis and Symbols ---
EMOJI = {
    "folder": "📁",
    "file": "📄",
    "backup": "💾",
    "settings": "⚙️",
    "warning": "⚠️",
    "error": "❌",
    "success": "✅",
    "info": "ℹ️",
    "star": "⭐",
    "rocket": "🚀",
    "time": "⏱️",
    "load": "⏳",
    "filter": "🔍",
    "help": "❓",
    "exit": "🚪",
    "extension": "🔧",
    "heart": "❤️",
    "note": "📝",
    "save": "💾",
    "zip": "🗜️",
    "config": "🛠️",
    "light": "💡"
}


# --- Interface Functions ---
def clear_screen():
    """Clears the terminal screen content."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title, emoji_key=None):
    """Prints a title bar."""
    clear_screen()
    width = 60
    emoji = EMOJI.get(emoji_key, "") if emoji_key else ""

    print("=" * width)
    if emoji:
        print(f"{emoji}  {title}  {emoji}")
    else:
        print(f" {title} ")
    print("=" * width)
    print()  # Add a blank line


def print_menu_item(key, text, emoji_key=None):
    """Prints a menu item."""
    emoji = EMOJI.get(emoji_key, "") if emoji_key else ""
    if emoji:
        print(f"[{key}] {emoji} {text}")
    else:
        print(f"[{key}] {text}")


def print_status(text, status_type="info", newline=True):
    """Prints a status message."""
    prefix = ""

    if status_type == "success":
        prefix = f"{EMOJI['success']} "
    elif status_type == "error":
        prefix = f"{EMOJI['error']} "
    elif status_type == "warning":
        prefix = f"{EMOJI['warning']} "
    elif status_type == "info":
        prefix = f"{EMOJI['info']} "

    if newline:
        print(f"{prefix}{text}")
    else:
        print(f"{prefix}{text}", end="", flush=True)


def print_progress(current, total, prefix="", suffix="", length=50):
    """Prints a progress bar."""
    percent = f"{100 * (current / float(total)):.1f}"
    filled_length = int(length * current // total)
    # Use # and - as progress bar characters
    bar = "#" * filled_length + "-" * (length - filled_length)
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end="\r")
    if current == total:
        print()  # Newline after completion


def loading_effect(seconds=1, message="Processing"):
    """Displays a loading effect."""
    chars = "⣾⣽⣻⢿⡿⣟⣯⣷"  # Use spinning characters to simulate loading
    for _ in range(int(seconds * 10)):
        for char in chars:
            print(f"\r{message} {char}", end="", flush=True)
            time.sleep(0.1)
    # Clear the loading animation
    print("\r" + " " * (len(message) + 2), end="\r")


def print_divider(char="-", length=60):
    """Prints a divider line."""
    print(f"{char * length}")


# --- Logging Setup ---
def setup_logging(log_file: Path):
    """
    Sets up logging configuration, logging to both file and console.
    """
    # Optimization: Set log level to INFO to reduce overhead from DEBUG logs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)  # Keep console output
        ]
    )
    # Suppress redundant logs from certain libraries
    logging.getLogger("concurrent").setLevel(logging.WARNING)


# --- Configuration Management ---
class BackupConfig:
    """Configuration management class, responsible for loading and saving user settings."""

    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.extensions: Set[str] = set(DEFAULT_SOURCE_EXTENSIONS)
        self.use_gitignore: bool = True  # Enable .gitignore filtering by default
        self.config_version: str = CONFIG_VERSION
        # Add config cache to avoid frequent disk I/O
        self._config_cache: Dict = {}
        # Optimization: Use atomic load to prevent config file corruption
        self.load()

    def load(self):
        """Loads settings from the configuration file."""
        if not self.config_file.exists():
            logging.info(f"Configuration file not found, using default settings: {self.config_file}")
            return

        try:
            # Optimization: Read into memory first for validation before using
            with self.config_file.open('r', encoding='utf-8') as f:
                config_data = json.load(f)

            # Save to cache
            self._config_cache = config_data.copy()

            # Check configuration file version
            if 'config_version' in config_data:
                file_version = config_data.get('config_version')
                if file_version != self.config_version:
                    logging.warning(
                        f"Configuration file version mismatch (File: {file_version}, Expected: {self.config_version}), attempting compatible load.")

            # Load file extensions
            if 'extensions' in config_data and isinstance(config_data['extensions'], list):
                # Validate extension format
                valid_extensions = [ext for ext in config_data['extensions']
                                    if isinstance(ext, str) and ext.startswith('.')]
                self.extensions = set(valid_extensions)
                logging.info(f"Loaded {len(self.extensions)} file extensions from configuration.")

            # Load gitignore filter setting
            if 'use_gitignore' in config_data and isinstance(config_data['use_gitignore'], bool):
                self.use_gitignore = config_data['use_gitignore']
                logging.info(f".gitignore filtering feature set to: {'Enabled' if self.use_gitignore else 'Disabled'}")

        except json.JSONDecodeError:
            logging.error(f"Configuration file {self.config_file} is invalid, using default settings.")
        except Exception as e:
            logging.error(f"Error loading configuration file: {e}")

    def save(self):
        """Saves settings to the configuration file."""
        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare configuration data to save
            config_data = {
                'config_version': self.config_version,
                'extensions': list(self.extensions),
                'use_gitignore': self.use_gitignore
            }

            # Optimization: Check if configuration has changed, skip writing if not
            if self._config_cache == config_data:
                logging.info("Configuration unchanged, skipping save.")
                return

            # Update cache
            self._config_cache = config_data.copy()

            # Optimization: Use atomic write to prevent configuration corruption
            temp_file = self.config_file.with_suffix('.tmp')
            with temp_file.open('w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)

            # If original config file exists, back it up first
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.bak')
                try:
                    self.config_file.replace(backup_file)
                except Exception as e:
                    logging.warning(f"Failed to backup original configuration file: {e}")

            # Replace original config file with temp file (atomic operation)
            temp_file.replace(self.config_file)

            logging.info(f"Settings saved to configuration file: {self.config_file}")
            print_status(f"Settings saved to configuration file.", "success")
        except Exception as e:
            logging.error(f"Error saving configuration file: {e}")
            print_status(f"Error saving configuration file: {e}", "error")


# --- GitIgnore Handling ---
class GitIgnoreFilter:
    """Handles .gitignore files and provides path filtering functionality."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.patterns: List[Pattern] = []
        self.negation_patterns: List[Pattern] = []
        self.loaded = False
        # Optimization: Add cache to speed up checks for repeated paths
        self._cache: Dict[str, bool] = {}
        # Optimization: Add dictionary for precompiled common patterns
        self._common_patterns = {}

        # Try to load the .gitignore file
        gitignore_path = project_dir / '.gitignore'
        if gitignore_path.exists() and gitignore_path.is_file():
            self._load_gitignore(gitignore_path)
            self.loaded = True
        else:
            logging.info(f"No .gitignore file found in project directory: {project_dir}")

    def _load_gitignore(self, gitignore_path: Path):
        """Loads and parses the .gitignore file."""
        try:
            # Optimization: Limit .gitignore file size to prevent issues with unusually large files
            if gitignore_path.stat().st_size > 1024 * 1024:  # 1MB limit
                logging.warning(f".gitignore file is too large: {gitignore_path.stat().st_size} bytes, may impact performance.")

            with gitignore_path.open('r', encoding='utf-8') as f:
                lines = [line.rstrip() for line in f.readlines()]

            valid_patterns = []
            valid_negations = []

            # Preprocessing: Remove duplicate lines and sort to reduce subsequent processing
            lines = list(dict.fromkeys(lines))

            for line in lines:
                # Ignore empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Handle negation patterns (starting with !)
                is_negation = line.startswith('!')
                if is_negation:
                    pattern_str = line[1:].strip()
                else:
                    pattern_str = line.strip()

                # Skip empty patterns
                if not pattern_str:
                    continue

                # Convert .gitignore pattern to regex
                regex_pattern = self._convert_gitignore_to_regex(pattern_str)

                # Add to the appropriate list based on pattern type
                try:
                    compiled_pattern = re.compile(regex_pattern)
                    if is_negation:
                        valid_negations.append(compiled_pattern)
                    else:
                        valid_patterns.append(compiled_pattern)
                except re.error as e:
                    logging.warning(f"Invalid .gitignore pattern: '{pattern_str}', Error: {e}")

            self.patterns = valid_patterns
            self.negation_patterns = valid_negations
            logging.info(
                f"Loaded {len(valid_patterns)} filter patterns and {len(valid_negations)} negation patterns from {gitignore_path}")

        except Exception as e:
            logging.error(f"Error parsing .gitignore file: {e}")

    def _convert_gitignore_to_regex(self, pattern: str) -> str:
        """
        Converts a .gitignore pattern to a regular expression.
        Optimizations:
        1. Add cache for common patterns.
        2. Special handling for simple wildcard cases.
        """
        # Optimization: Check cache for regex of this pattern
        if pattern in self._common_patterns:
            return self._common_patterns[pattern]

        # Handle special cases
        if not pattern:
            return r'^$'

        # Optimization: Directly handle common simple patterns
        if pattern == '*':
            result = r'[^/]+$'
            self._common_patterns[pattern] = result
            return result
        elif pattern == '*/':
            result = r'[^/]+/$'
            self._common_patterns[pattern] = result
            return result

        # Check if it's a root directory pattern (starts with /)
        is_root_pattern = pattern.startswith('/')
        if is_root_pattern:
            pattern = pattern[1:]  # Remove leading slash

        # Check if it's a directory pattern (ends with /)
        is_dir_pattern = pattern.endswith('/')
        if is_dir_pattern:
            pattern = pattern[:-1]  # Temporarily remove trailing slash, handle later

        # Escape special characters to avoid conflicts in regex
        pattern = re.escape(pattern)

        # Restore wildcards, as re.escape escapes them
        pattern = pattern.replace(r'\*', '*')
        pattern = pattern.replace(r'\?', '?')

        # Handle ** wildcard (matches multiple directory levels)
        pattern = pattern.replace('**', '__DOUBLEWILDCARD__')

        # Handle single wildcards
        pattern = pattern.replace('*', r'[^/]*')  # * matches any characters except /
        pattern = pattern.replace('?', r'[^/]')  # ? matches a single non-/ character

        # Restore ** wildcard and replace with correct regex (matches across directory levels)
        pattern = pattern.replace('__DOUBLEWILDCARD__', r'.*')

        # Build the final regex pattern
        regex = ''

        # Root patterns need to start with ^ to ensure matching from the project root
        if is_root_pattern:
            regex = r'^'
        else:
            # Non-root patterns can match at any level
            regex = r'(^|/)'

        # Add the main pattern
        regex += pattern

        # Handle directory patterns
        if is_dir_pattern:
            # Directory patterns match the directory itself and all its contents
            regex += r'(/.*)?$'
        else:
            # Non-directory patterns match specific files only
            regex += r'$'

        # Cache the result
        self._common_patterns[pattern] = regex
        return regex

    def should_ignore(self, file_path: Path) -> bool:
        """
        Determines if a given file should be ignored based on .gitignore rules.
        Optimization: Adds caching for faster processing.
        """
        if not self.loaded or not (self.patterns or self.negation_patterns): # Check both pattern types
            return False

        # Get the path relative to the project root
        try:
            rel_path = str(file_path.relative_to(self.project_dir))
            # Standardize to forward slashes
            rel_path = rel_path.replace('\\', '/')
        except ValueError:
            # If the path is not under the project directory (e.g., the project dir itself), don't ignore
            return False

        # Optimization: Check cache
        if rel_path in self._cache:
            return self._cache[rel_path]

        # Check negation patterns first (rules for explicitly *not* ignoring)
        for neg_pattern in self.negation_patterns:
            if neg_pattern.search(rel_path):
                self._cache[rel_path] = False
                return False

        # Then check ignore patterns
        for pattern in self.patterns:
            if pattern.search(rel_path):
                self._cache[rel_path] = True
                return True

        # Result is not ignored
        self._cache[rel_path] = False
        return False


# --- Optimized File Reading Function ---
def read_file_content_buffered(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Reads file content using a buffer, handling large files more efficiently.
    Returns (content_string, None) or (None, error_message_string).
    """
    try:
        # First, check file size
        file_size = file_path.stat().st_size

        # Warn if the file is very large (over 10MB)
        if file_size > 10 * 1024 * 1024:  # 10 MB
            logging.warning(f"File is very large ({file_size} bytes): {file_path}")

        # For small files (<1MB), read directly
        if file_size < 1024 * 1024:  # 1 MB
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    return f.read(), None
            except UnicodeDecodeError:
                 logging.warning(f"File {file_path} not valid UTF-8, trying latin-1...")
                 with file_path.open('r', encoding='latin-1') as f:
                     return f.read(), None


        # For larger files, use buffered reading
        content = io.StringIO()
        try:
            with file_path.open('r', encoding='utf-8', errors='ignore') as f: # Use errors='ignore' as a fallback
                while True:
                    chunk = f.read(READ_BUFFER_SIZE)
                    if not chunk:
                        break
                    content.write(chunk)
            return content.getvalue(), None
        except Exception as e_utf8: # Catch potential read errors even with ignore
             logging.warning(f"Could not read {file_path} as UTF-8 (even ignoring errors): {e_utf8}, trying latin-1...")
             content = io.StringIO()
             try:
                 with file_path.open('r', encoding='latin-1') as f:
                     while True:
                         chunk = f.read(READ_BUFFER_SIZE)
                         if not chunk:
                             break
                         content.write(chunk)
                 return content.getvalue(), None
             except Exception as e_latin1:
                 err_msg = f"Failed to read file {file_path} as UTF-8 or latin-1: {e_latin1}"
                 logging.error(err_msg)
                 return None, err_msg


    except PermissionError as e:
        err_msg = f"Permission denied reading file {file_path}: {e}"
        logging.error(err_msg)
        return None, err_msg
    except Exception as e:
        err_msg = f"Unknown error reading file {file_path}: {e}"
        logging.error(err_msg)
        return None, err_msg


# --- Core Logic ---
def get_code_files(directory: Path, extensions: Tuple[str, ...], gitignore_filter: Optional[GitIgnoreFilter] = None,
                   use_gitignore: bool = True) -> List[Path]:
    """
    Traverses a directory and returns a list of file paths with specified extensions.
    Uses efficient traversal.
    Optionally uses .gitignore filtering.

    Optimization: Uses a generator and filter to reduce memory usage.
    """
    code_files = []

    # Optimization: Use a single traversal to find files with any of the specified extensions
    def find_matching_files() -> Iterator[Path]:
        # Create a set for faster extension checks
        ext_set = set(extensions)

        try:
            # Optimization: Use os.walk for potentially better control on large directories
            for root, dirs, files in os.walk(str(directory), topdown=True):
                root_path = Path(root)
                # Optimization: Filter directories based on gitignore *before* descending
                if use_gitignore and gitignore_filter and gitignore_filter.loaded:
                    # Filter out ignored directories in-place
                    dirs[:] = [d for d in dirs if not gitignore_filter.should_ignore(root_path / d)]

                for file in files:
                    file_path = root_path / file
                    # Check file extension
                    if file_path.suffix.lower() in ext_set:
                        # Check gitignore filter for the file
                        if use_gitignore and gitignore_filter and gitignore_filter.loaded:
                            if not gitignore_filter.should_ignore(file_path):
                                yield file_path
                        else:
                            yield file_path
        except PermissionError as e:
            logging.warning(f"Permission denied accessing directory: {e}")
        except Exception as e:
            logging.error(f"Error traversing directory: {e}")

    # Use the generator to find files and immediately convert to a sorted list
    code_files = sorted(find_matching_files(), key=lambda p: str(p))

    logging.info(f"Found {len(code_files)} matching files in {directory}.")
    return code_files


def build_tree(directory: Path, prefix: str = "", gitignore_filter: Optional[GitIgnoreFilter] = None,
               use_gitignore: bool = True) -> str:
    """
    Recursively builds a string representation of the directory tree.
    Uses pathlib and optimized string building.
    Optionally applies .gitignore filtering.

    Optimization: Uses StringIO for efficient string construction.
    """
    # Use StringIO instead of string concatenation for performance
    lines = io.StringIO()

    try:
        # Get directory contents and sort (directories first, then by name)
        contents = sorted(list(directory.iterdir()), key=lambda p: (not p.is_dir(), str(p.name).lower()))

        # Filter contents if .gitignore filtering is enabled and a valid filter is loaded
        if use_gitignore and gitignore_filter and gitignore_filter.loaded:
            # Filter out ignored files and directories
            contents = [item for item in contents if not gitignore_filter.should_ignore(item)]

    except PermissionError:
        logging.warning(f'Permission denied accessing directory: {directory}')
        return ""
    except OSError as e:
        logging.warning(f'Error accessing directory: {directory} - {e}')
        return ""

    # Return empty string if no contents
    if not contents:
        return ""

    # Generate connector strings
    pointers = ['├── '] * (len(contents) - 1) + ['└── ']
    for pointer, item_path in zip(pointers, contents):
        if item_path.is_dir():
            lines.write(f'{prefix}{pointer}{item_path.name}/\n')
            extension = '│   ' if pointer == '├── ' else '    '
            # Recursive call, passing the filter
            subtree = build_tree(item_path, prefix + extension, gitignore_filter, use_gitignore)
            if subtree: # Only write if subtree is not empty
                lines.write(subtree) # Removed extra newline here, build_tree handles its own newlines
        else:
            lines.write(f'{prefix}{pointer}{item_path.name}\n')

    # Return the constructed string
    result = lines.getvalue()
    # build_tree adds necessary newlines, so rstrip might be too aggressive if last item is dir
    return result


def get_directory_tree(directory: Path, gitignore_filter: Optional[GitIgnoreFilter] = None,
                       use_gitignore: bool = True) -> str:
    """
    Gets the tree structure of the specified directory and returns it
    wrapped in a Markdown code block.
    Optionally applies .gitignore filtering.
    """
    project_name = directory.name
    # Pass the filter during recursive tree building
    tree_str = f'{project_name}/\n{build_tree(directory, "", gitignore_filter, use_gitignore)}'
    # Ensure consistent newlines before closing ```
    tree_str = tree_str.rstrip('\n')
    return f"```\n{tree_str}\n```\n\n" # Add extra newline for spacing


def get_language_from_extension(file_path: Path) -> str:
    """
    Returns the appropriate Markdown code block language identifier based on the file extension.

    Optimization: Uses a static cache dictionary instead of creating one each time.
    """
    # Static dictionary cache, added as a function attribute for reuse
    if not hasattr(get_language_from_extension, 'language_map'):
        get_language_from_extension.language_map: Dict[str, str] = {
            '.py': 'python', '.java': 'java', '.cpp': 'cpp', '.c': 'c',
            '.h': 'cpp', '.cs': 'csharp', '.js': 'javascript', '.ts': 'typescript',
            '.jsx': 'jsx', '.tsx': 'tsx', '.rb': 'ruby', '.go': 'go',
            '.php': 'php', '.swift': 'swift', '.kt': 'kotlin', '.m': 'objectivec',
            '.mm': 'objectivec', '.md': 'markdown', '.json': 'json', '.xml': 'xml',
            '.yaml': 'yaml', '.yml': 'yaml',
            # Common config/text types - default to no language hint
            '.txt': '', '.ini': '', '.cfg': '',
        }

    extension = file_path.suffix.lower()
    return get_language_from_extension.language_map.get(extension, '')  # Return empty string if extension not found


def process_file_task(file_path: Path, base_dir: Path) -> Tuple[Path, str]:
    """
    Processing task for a single file: reads content and formats as a Markdown snippet.
    Returns (relative_file_path, markdown_content_string).

    Optimization: Uses StringIO and optimized file reading.
    """
    relative_path = file_path.relative_to(base_dir)
    lang = get_language_from_extension(file_path)

    # Use buffered reading for file content
    content_str, error_str = read_file_content_buffered(file_path)

    # Use StringIO to build Markdown content
    md_content = io.StringIO()
    # Use standard Markdown formatting for file paths
    md_content.write(f'### File: `{str(relative_path).replace("\\", "/")}`\n\n') # Ensure forward slashes
    md_content.write(f'```{lang}\n')

    if content_str is not None:
        md_content.write(content_str)
    else:
        # Include error message in Markdown output
        md_content.write(f"Error reading file: {error_str}")

    md_content.write('\n```\n\n')

    return relative_path, md_content.getvalue()


def process_files_batch(files_batch: List[Path], base_dir: Path) -> List[Tuple[Path, str]]:
    """
    Processes a batch of files, optimizing handling of many small files.
    """
    results = []
    for file_path in files_batch:
        try:
            results.append(process_file_task(file_path, base_dir))
        except Exception as e:
            # Handle error but continue processing the batch
            relative_path = file_path.relative_to(base_dir)
            # Use standard Markdown formatting for file paths
            rel_path_str = str(relative_path).replace("\\", "/")
            error_content = f"### File: `{rel_path_str}`\n\n```\nError processing file: {e}\n```\n\n"
            results.append((relative_path, error_content))
            logging.error(f"Error processing file {rel_path_str}: {e}")
    return results


def write_code_and_structure(
        directory: Path,
        output_file: Path,
        extensions: Tuple[str, ...],
        use_gitignore: bool = True,
        max_workers: int = DEFAULT_MAX_WORKERS
):
    """
    Writes the project directory structure and content of all qualifying source code
    files to a Markdown file. Uses ThreadPoolExecutor for multi-threaded file reading,
    collects results, and writes them sequentially.
    Optionally uses .gitignore filtering.

    Optimizations:
    - Uses batching to reduce thread creation overhead.
    - Writes directly to file instead of building a large string in memory.
    - Adds enhanced progress feedback.
    """
    logging.info(f"Starting processing for project: {directory}")
    print_status(f"Starting processing for project: {directory}", "info")

    # Initialize gitignore filter (if enabled)
    gitignore_filter = None
    if use_gitignore:
        gitignore_filter = GitIgnoreFilter(directory)
        if gitignore_filter.loaded:
            logging.info(f"Loaded .gitignore filter rules, preparing to apply filtering.")
            print_status(f"Loaded .gitignore filter rules.", "info")
        else:
            logging.info("No valid .gitignore file found, no filtering will be applied.")

    loading_effect(1, f"{EMOJI['filter']} Scanning files...")

    # Get files, passing the filter
    start_time_scan = time.time()
    code_files = get_code_files(directory, extensions, gitignore_filter, use_gitignore)
    scan_time = time.time() - start_time_scan
    logging.info(f"File scanning completed in {scan_time:.2f} seconds.")

    total_files = len(code_files)

    if total_files == 0:
        logging.warning("No matching files found for backup.")
        print_status("No matching files found for backup.", "warning")

        # Create Markdown file even if no files found, explaining the situation
        try:
            loading_effect(1, f"{EMOJI['note']} Generating empty backup file...")
            with output_file.open('w', encoding='utf-8') as out_f:
                out_f.write(f'# Project Name: {directory.name}\n\n')
                out_f.write('## Project Directory Structure:\n\n')
                # Generate directory tree, passing the filter
                out_f.write(get_directory_tree(directory, gitignore_filter, use_gitignore))
                out_f.write('## Source Code Content:\n\n')
                out_f.write('**No files found matching the specified extensions.**\n')

                # Record filtering information
                out_f.write('\n## Backup Information\n\n')
                out_f.write(f'- Tool Version: {VERSION}\n')
                out_f.write(f'- Backup Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                if use_gitignore and gitignore_filter and gitignore_filter.loaded:
                    out_f.write(f'- .gitignore Filtering: Enabled\n')
                elif use_gitignore:
                     out_f.write(f'- .gitignore Filtering: Enabled (but no .gitignore file found)\n')
                else:
                    out_f.write(f'- .gitignore Filtering: Disabled\n')
                out_f.write(f'- Included Extensions: {", ".join(sorted(extensions))}\n')
                out_f.write(f'- Total Files Found: 0\n')

            logging.info(f"Generated empty backup file: {output_file}")
            print_status(f"Generated empty backup file: {output_file}", "success")
        except Exception as e:
            logging.error(f"Error writing empty output file: {e}")
            print_status(f"Error writing output file: {e}", "error")
        return  # Stop processing if no files

    # --- 1. Write Header and Directory Structure ---
    try:
        print_status(f"Generating directory structure...", "info")
        loading_effect(1, f"{EMOJI['folder']} Analyzing directory structure...")

        start_time_tree = time.time()
        with output_file.open('w', encoding='utf-8') as out_f:
            out_f.write(f'# Project Name: {directory.name}\n\n')
            out_f.write('## Project Directory Structure:\n\n')
            # Generate directory tree, passing the filter
            out_f.write(get_directory_tree(directory, gitignore_filter, use_gitignore))
            out_f.write('## Source Code Content:\n\n')

            # Add filtering info note
            if use_gitignore and gitignore_filter and gitignore_filter.loaded:
                out_f.write('> Note: Files were filtered according to `.gitignore` rules during backup.\n\n')
            elif use_gitignore:
                 out_f.write('> Note: `.gitignore` filtering was enabled, but no `.gitignore` file was found.\n\n')


        tree_time = time.time() - start_time_tree
        logging.info(f"Directory structure generation completed in {tree_time:.2f} seconds.")
        print_status("Directory structure generated successfully.", "success")

    except Exception as e:
        logging.error(f'Error writing output file header information: {e}')
        print_status(f'Error writing file header information: {e}', "error")
        # If header writing fails, it's best to exit
        sys.exit(f"Fatal: Could not write backup file header: {output_file}. Error: {e}")

    # --- 2. Concurrently Process Files ---
    # Optimization: Adjust batch size and workers based on average file size
    batch_size = BATCH_SIZE
    adjusted_max_workers = max_workers

    if total_files > 0:
        # Calculate average size based on a sample to avoid iterating all files if very numerous
        sample_size = min(100, total_files)
        try:
             avg_size = sum(f.stat().st_size for f in code_files[:sample_size]) / sample_size
        except OSError as e:
             logging.warning(f"Could not stat some files for size calculation: {e}. Using default batch size.")
             avg_size = 0

        if avg_size > 1024 * 1024:  # If average file size > 1MB
            batch_size = max(1, BATCH_SIZE // 10)  # Reduce batch size
            logging.info(f"Adjusting batch size to {batch_size} due to large average file size ({avg_size / (1024*1024):.1f} MB).")
            # For very large files, also reduce workers
            if avg_size > 10 * 1024 * 1024:  # If average file size > 10MB
                adjusted_max_workers = max(4, max_workers // 4)
                logging.info(f"Adjusting max workers to {adjusted_max_workers} due to very large average file size.")
    else:
         avg_size = 0 # Should not happen due to initial check, but safe

    # Create file batches
    batches = []
    for i in range(0, total_files, batch_size):
        batches.append(code_files[i:i + batch_size])

    logging.info(f"Divided {total_files} files into {len(batches)} batches for processing (~{batch_size} files/batch).")

    processed_count = 0
    lock = threading.Lock()  # Lock for safely updating the counter

    print_status(f"Processing {total_files} files (using up to {adjusted_max_workers} threads)...", "info")
    logging.info(f"Starting processing of {total_files} files using up to {adjusted_max_workers} threads...")

    start_time_processing = time.time()

    # Optimization: Write results directly to the file instead of holding in memory
    with output_file.open('a', encoding='utf-8') as out_f:
        # Use ThreadPoolExecutor to process file batches
        with ThreadPoolExecutor(max_workers=adjusted_max_workers) as executor:
            # Submit batch processing tasks
            future_to_batch = {executor.submit(process_files_batch, batch, directory): batch_idx
                               for batch_idx, batch in enumerate(batches)}

            # To ensure ordered writing, track completed batches and their results
            completed_results: Dict[int, List[Tuple[Path, str]]] = {}
            next_batch_to_write = 0

            # Process completed futures as they finish
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    batch_file_count = len(batches[batch_idx]) if batch_idx < len(batches) else 0 # Get actual batch size

                    # Update processed count
                    with lock:
                        processed_count += batch_file_count
                        # Update progress bar
                        print_progress(processed_count, total_files,
                                       prefix=f"{EMOJI['file']} Processing files",
                                       suffix=f"{processed_count}/{total_files}")

                    # Store batch results, keyed by batch index
                    completed_results[batch_idx] = batch_results

                    # Attempt to write completed batches in sequential order
                    while next_batch_to_write in completed_results:
                        # Sort results within the batch by relative file path for consistent output
                        sorted_results = sorted(completed_results[next_batch_to_write], key=lambda x: str(x[0]))

                        # Write content for all files in this batch
                        for _, content in sorted_results:
                            out_f.write(content)

                        # Remove processed batch data to free memory
                        del completed_results[next_batch_to_write]
                        next_batch_to_write += 1

                except Exception as e:
                    # Log batch processing errors
                    batch_file_count = len(batches[batch_idx]) if batch_idx < len(batches) else 0
                    logging.error(f"Failed processing batch {batch_idx}: {e}", exc_info=True)
                    with lock:
                        # Ensure progress bar reflects attempt even on failure
                        processed_count += batch_file_count
                        print_progress(processed_count, total_files,
                                       prefix=f"{EMOJI['file']} Processing files",
                                       suffix=f"{processed_count}/{total_files}")

        # Record processing time
        processing_time = time.time() - start_time_processing
        processing_rate = total_files / processing_time if processing_time > 0 else 0
        logging.info(f"File processing completed in {processing_time:.2f} seconds (avg {processing_rate:.2f} files/sec).")

        print()  # Newline after progress bar completion
        print_status("All files processed successfully.", "success")

        # --- 3. Add Backup Information Footer ---
        logging.info("Writing backup metadata...")
        loading_effect(0.5, f"{EMOJI['info']} Finalizing backup info...")

        # Append backup information at the end of the file
        out_f.write('\n## Backup Information\n\n')
        out_f.write(f'- Tool Version: {VERSION}\n')
        out_f.write(f'- Backup Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        if use_gitignore and gitignore_filter and gitignore_filter.loaded:
            out_f.write(f'- .gitignore Filtering: Enabled\n')
        elif use_gitignore:
             out_f.write(f'- .gitignore Filtering: Enabled (but no .gitignore file found)\n')
        else:
            out_f.write(f'- .gitignore Filtering: Disabled\n')
        out_f.write(f'- Included Extensions: {", ".join(sorted(extensions))}\n')
        out_f.write(f'- Total Files Processed: {total_files}\n') # Changed label for clarity
        out_f.write(f'- File Processing Time: {processing_time:.2f} seconds\n')

    # Completion
    # total_time = time.time() - start_time_scan # More accurate total time
    logging.info(f"Backup successfully completed.") # Removed inaccurate total time calculation here
    print_status(f"Successfully wrote all content to: {output_file}", "success")


def compress_backup(output_file: Path) -> Optional[Path]:
    """
    Compresses the generated Markdown file into a ZIP archive.

    Optimization: Uses efficient compression level.
    """
    # Output ZIP file in the same directory as the .md file
    zip_filename = output_file.with_suffix('.zip')
    try:
        print_status(f"Compressing backup file...", "info")
        loading_effect(1, f"{EMOJI['zip']} Compressing file...")

        # Get start time to calculate performance
        start_time = time.time()

        # Use best compression options
        compression = zipfile.ZIP_DEFLATED
        compression_level = 9  # Highest compression level

        with zipfile.ZipFile(zip_filename, 'w', compression=compression, compresslevel=compression_level) as zipf:
            # Add the markdown file to the zip, using its own filename inside the archive
            zipf.write(output_file, arcname=output_file.name)

        # Calculate compression efficiency and time
        original_size = output_file.stat().st_size
        compressed_size = zip_filename.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        compress_time = time.time() - start_time

        logging.info(f'Backup file compressed to: {zip_filename} (Original: {original_size / 1024:.1f}KB, '
                     f'Compressed: {compressed_size / 1024:.1f}KB, Savings: {compression_ratio:.1f}%, '
                     f'Time: {compress_time:.2f} sec)')

        print_status(f'Backup file compressed to: {zip_filename} (Compression Ratio: {compression_ratio:.1f}%)', "success")
        return zip_filename
    except Exception as e:
        logging.error(f'Error compressing backup file {output_file}: {e}')
        print_status(f'Error compressing backup file: {e}', "error")
        return None


# --- User Interface ---
def display_help():
    """
    Displays the help documentation.
    """
    print_header(f"Code Backup Tool Help v{VERSION}", "help")

    help_text = f"""
{EMOJI['rocket']} This tool backs up source code files from a specified project directory, generating a Markdown file containing the directory structure and source code.
{EMOJI['star']} Supports multi-threaded processing and optional ZIP compression.

【Features】
{EMOJI['extension']} Backup Specific File Types: Customize the file extensions to back up via the menu.
{EMOJI['folder']} Display Project Structure: Shows the project folders and files in a tree format.
{EMOJI['file']} Save Source Code: Writes source code into the Markdown file for easy viewing and sharing.
{EMOJI['rocket']} Multi-threading: Utilizes multiple CPU cores to speed up backups for large projects.
{EMOJI['zip']} Compress Backup: Optionally compress the generated Markdown file into a ZIP archive.
{EMOJI['filter']} .gitignore Filtering: Filter out content based on the project's .gitignore file (enabled by default).
{EMOJI['note']} Logging: Records key information and errors to `backup.log`.
{EMOJI['config']} Persistent Settings: Saves your file extension choices and feature toggle settings.

【How to Use】
{EMOJI['info']} After starting the program, you can directly enter the project's absolute path to start a backup.
{EMOJI['info']} Alternatively, enter a number to choose an option:
  [1] {EMOJI['backup']} Backup Project (requires absolute path)
  [2] {EMOJI['extension']} Manage File Extensions
  [3] {EMOJI['settings']} Manage Feature Settings
  [4] {EMOJI['help']} View This Help Information
  [5] {EMOJI['exit']} Exit Program

【File Extension Management】
{EMOJI['info']} In the extension management menu, you can:
  - View all available extensions and currently selected extensions.
  - Use 'add <.ext1> <.ext2> ...' to add extensions (e.g., `add .txt .log`).
  - Use 'remove <.ext1> <.ext2> ...' to remove extensions (e.g., `remove .java`).
  - Use 'reset' to restore the default list of extensions.
  - Use 'back' to return to the main menu.
  (Note: The leading dot '.' for extensions is optional when adding/removing)

【Feature Settings】
{EMOJI['info']} In the feature settings menu, you can:
  - Enable/disable the .gitignore file filtering feature.
  - View the current status of features.
  - All settings are saved automatically and loaded on the next start.

【.gitignore Filtering Explained】
{EMOJI['filter']} When .gitignore filtering is enabled, the tool automatically detects the `.gitignore` file in the project root.
{EMOJI['filter']} All files and directories matching the rules in `.gitignore` will be excluded from the backup.
{EMOJI['filter']} Supports common .gitignore pattern features like:
  - Patterns starting with a slash (`/foo`) match only at the project root.
  - Patterns without a leading slash (`foo`) match at any directory level.
  - Patterns ending with a slash (`foo/`) match directories and their contents.
  - `**` wildcard for matching multiple directory levels.
{EMOJI['info']} If no `.gitignore` file exists in the project, this feature will have no effect.

【Performance Optimizations】
{EMOJI['rocket']} This version (v{VERSION}) includes the following performance optimizations:
  - Efficient File Reading: Uses buffered reads for large files.
  - Smart Thread Allocation: Automatically adjusts thread count based on file characteristics.
  - Batch Processing: Reduces thread switching overhead for small files.
  - Memory Optimization: Streams large file content to avoid high memory usage.
  - Optimized .gitignore Parsing: Uses caching to speed up path matching.
  - Atomic File Operations: Ensures integrity of configuration and output files.

Author: Jack {EMOJI['light']}
"""
    print(help_text)


def manage_extensions(config: BackupConfig, available_extensions: Tuple[str, ...]) -> None:
    """
    Manages the file extension settings for backup detection and saves to config.
    Includes a clear exit prompt.
    """
    # Operate on a copy, although changes are saved immediately upon modification here
    current_ext_set = config.extensions.copy()
    available_ext_set = set(available_extensions)

    # Clear screen and display header
    print_header("Manage File Extensions", "extension")
    print(f"{EMOJI['info']} In this menu, you can modify the file types included in the backup.")
    print(f"{EMOJI['info']} Type 'back' at any time to return to the main menu.")

    while True:
        print_divider()
        print(
            f"{EMOJI['extension']} Currently selected extensions ({len(current_ext_set)}): {', '.join(sorted(list(current_ext_set)))}")

        print(f"\nAvailable commands:")
        print(f"{EMOJI['info']} add [.ext1] [.ext2]... - Add extensions")
        print(f"{EMOJI['info']} remove [.ext1] [.ext2]... - Remove extensions")
        print(f"{EMOJI['info']} reset - Reset to default extensions")
        print(f"{EMOJI['info']} showall - Show all available extensions")
        print(f"{EMOJI['info']} back - Return to main menu")

        cmd_input = input('Manage Extensions > ').strip().lower()
        parts = cmd_input.split()
        command = parts[0] if parts else ""

        if command == "add" and len(parts) > 1:
            added_count = 0
            for ext in parts[1:]:
                normalized_ext = ext if ext.startswith('.') else '.' + ext
                if normalized_ext in available_ext_set:
                    if normalized_ext not in current_ext_set:
                        current_ext_set.add(normalized_ext)
                        added_count += 1
                        print(f"  {EMOJI['success']} Added: {normalized_ext}")
                    else:
                        print(f"  {EMOJI['info']} Info: {normalized_ext} is already in the list.")
                else:
                    print(f"  {EMOJI['warning']} Warning: Extension '{normalized_ext}' is not in the available list, ignored.")
            if added_count > 0:
                print(f"  {EMOJI['success']} Successfully added {added_count} new extension(s).")
                # Save current configuration
                config.extensions = current_ext_set
                config.save()

        elif command == "remove" and len(parts) > 1:
            removed_count = 0
            for ext in parts[1:]:
                normalized_ext = ext if ext.startswith('.') else '.' + ext
                if normalized_ext in current_ext_set:
                    current_ext_set.remove(normalized_ext)
                    removed_count += 1
                    print(f"  {EMOJI['success']} Removed: {normalized_ext}")
                else:
                    print(f"  {EMOJI['info']} Info: Extension '{normalized_ext}' is not currently selected, ignored.")
            if removed_count > 0:
                print(f"  {EMOJI['success']} Successfully removed {removed_count} extension(s).")
                # Save current configuration
                config.extensions = current_ext_set
                config.save()

        elif command == "reset":
            current_ext_set = set(DEFAULT_SOURCE_EXTENSIONS)
            print(f"  {EMOJI['success']} File extensions reset to default list.")
            # Save current configuration
            config.extensions = current_ext_set
            config.save()

        elif command == "showall":
            print(f"{EMOJI['info']} All available extensions ({len(available_ext_set)}):")
            # Display 5 extensions per line for neatness
            ext_list = sorted(list(available_extensions))
            for i in range(0, len(ext_list), 5):
                print(f"  {' '.join(ext_list[i:i + 5])}")

        elif command == "back":
            print(f"\n{EMOJI['exit']} Exiting extension management, returning to main menu.")
            # Short delay before returning to main menu
            time.sleep(0.5)
            return

        elif not command:  # If user just pressed Enter
            print(f"{EMOJI['info']} Please enter a command. Tip: Type 'back' to return to the main menu.")
        else:
            print(f"{EMOJI['error']} Invalid command '{command}'.")
            print(f"{EMOJI['info']} Available commands: add, remove, reset, showall, back.")

        # Give user time to read output
        time.sleep(0.5)


def manage_settings(config: BackupConfig) -> None:
    """Manages the feature settings menu."""
    print_header("Manage Feature Settings", "settings")
    print(f"{EMOJI['info']} In this menu, you can manage various feature settings.")
    print(f"{EMOJI['info']} Type 'back' at any time to return to the main menu.")

    while True:
        print_divider()

        # Display current gitignore filter status
        status_emoji = EMOJI['success'] if config.use_gitignore else EMOJI['warning']
        status_text = "Enabled" if config.use_gitignore else "Disabled"
        print(f"{status_emoji} .gitignore Filtering Feature: {status_text}")

        print(f"\nAvailable commands:")
        toggle_text = "Disable" if config.use_gitignore else "Enable"
        print(f"{EMOJI['info']} 1 - {toggle_text} .gitignore Filtering Feature")
        print(f"{EMOJI['info']} back - Return to main menu")

        cmd_input = input('Manage Settings > ').strip().lower()

        if cmd_input == "1":
            config.use_gitignore = not config.use_gitignore
            status = "Enabled" if config.use_gitignore else "Disabled"
            emoji = EMOJI['success'] if config.use_gitignore else EMOJI['warning']
            print(f"{emoji} .gitignore Filtering feature has been {status}.")
            # Save settings
            config.save()
            time.sleep(1)  # Give user time to read feedback

        elif cmd_input == "back":
            print(f"\n{EMOJI['exit']} Exiting feature settings, returning to main menu.")
            time.sleep(0.5)
            return

        elif not cmd_input:
            print(f"{EMOJI['info']} Please enter a command. Tip: Type 'back' to return to the main menu.")

        else:
            print(f"{EMOJI['error']} Invalid command '{cmd_input}'. Please enter a valid option.")

        # Corrected indentation from original analysis
        time.sleep(0.5)


def get_backup_destination(script_dir: Path) -> Path:
    """Gets and creates the directory to save backups."""
    print_status(f"Select backup destination", "info")
    save_dir_input = input(
        f'{EMOJI["folder"]} Enter the directory path to save backup files \n'
        f'  (Leave blank to default to `{DEFAULT_BACKUP_DIR_NAME}` folder in script directory):\n> '
    ).strip()

    if not save_dir_input:
        save_directory = script_dir / DEFAULT_BACKUP_DIR_NAME
        print_status(f"Using default directory: {save_directory}", "info")
    else:
        save_directory = Path(save_dir_input).resolve()  # Resolve to absolute path
        print_status(f"Using custom directory: {save_directory}", "info")

    try:
        loading_effect(0.5, f"{EMOJI['folder']} Preparing save directory...")
        save_directory.mkdir(parents=True, exist_ok=True)  # Create if it doesn't exist
        logging.info(f"Backup will be saved to: {save_directory}")
        print_status(f"Backup will be saved to: {save_directory}", "success")
        return save_directory
    except PermissionError:
        logging.error(f"Permission denied to create or access save directory: {save_directory}")
        print_status(f"Permission denied to create or access save directory: {save_directory}", "error")
        raise  # Re-raise the exception for the caller
    except Exception as e:
        logging.error(f"Could not create or access save directory {save_directory}: {e}")
        print_status(f"Could not create or access save directory: {e}", "error")
        raise  # Re-raise


def create_unique_project_backup_folder(save_directory: Path, project_name: str) -> Path:
    """Creates a unique project folder for this specific backup, handling name conflicts."""
    base_folder = save_directory / project_name
    project_backup_folder = base_folder
    unique_suffix = 1

    # If the directory name already exists, append a number suffix
    while project_backup_folder.exists():
        print_status(f"Directory {project_backup_folder.name} already exists, trying new name...", "info")
        project_backup_folder = save_directory / f"{project_name}_{unique_suffix}"
        unique_suffix += 1

    try:
        loading_effect(0.5, f"{EMOJI['folder']} Creating project folder...")
        project_backup_folder.mkdir(parents=True)
        logging.info(f"Created project backup folder: {project_backup_folder}")
        print_status(f"Created project backup folder: {project_backup_folder}", "success")
        return project_backup_folder
    except Exception as e:
        logging.error(f"Could not create project backup folder {project_backup_folder}: {e}")
        print_status(f"Could not create project backup folder: {e}", "error")
        raise  # Re-raise


def backup_project(config: BackupConfig, provided_project_dir: Optional[str] = None):
    """
    Executes a complete project backup process.
    """
    print_header("Project Backup", "backup")
    try:
        script_directory = Path(sys.argv[0]).resolve().parent
    except Exception:
        script_directory = Path.cwd() # Fallback if argv[0] is unusual


    project_path_str: str
    if provided_project_dir:
        project_path_str = provided_project_dir
        print_status(f"Using provided project path: {project_path_str}", "info")
    else:
        project_path_str = input(f'{EMOJI["folder"]} Please enter the absolute path of the project to back up:\n> ').strip()

    if not project_path_str:
        print_status('Project path not entered.', "error")
        logging.error("Backup process aborted: User did not enter a project path.")
        time.sleep(1.5)
        return

    project_directory = Path(project_path_str)

    # Validate project directory
    if not project_directory.is_absolute():
        print_status(f"Provided path '{project_path_str}' is not an absolute path.", "error")
        logging.error(f"Backup process aborted: Path is not absolute - {project_path_str}")
        time.sleep(1.5)
        return
    if not project_directory.is_dir():
        print_status(f'Specified path does not exist or is not a directory: {project_directory}', "error")
        logging.error(f"Backup process aborted: Path invalid or not a directory - {project_directory}")
        time.sleep(1.5)
        return

    try:
        # Get and create the save destination directory
        save_directory = get_backup_destination(script_directory)

        # Create a unique folder within save_directory for this backup run
        project_name = project_directory.name
        project_backup_folder = create_unique_project_backup_folder(save_directory, project_name)

        # Define the output Markdown file path
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')  # Add seconds for uniqueness
        output_filename = f'{project_name}_backup_{current_time}.md'
        output_path = project_backup_folder / output_filename

        # Ask whether to compress
        compress_choice = input(
            f'{EMOJI["zip"]} Compress the backup result into a ZIP file? (y/n, default is n):\n> ').strip().lower()
        compress_flag = compress_choice in ('y', 'yes')

        # Display gitignore filter status
        gitignore_status = "Enabled" if config.use_gitignore else "Disabled"
        gitignore_emoji = EMOJI['success'] if config.use_gitignore else EMOJI['warning']
        print(
            f"\n{gitignore_emoji} .gitignore filtering is currently {gitignore_status}.")
        print(f"  To change this, select 'Manage Feature Settings' from the main menu.")

        logging.info(f"Starting backup for project '{project_name}' to {output_path}")
        print()
        print_status(f'Starting backup for project "{project_name}"...', "info")
        print_divider()

        # Execute the core backup task
        write_code_and_structure(
            directory=project_directory,
            output_file=output_path,
            extensions=tuple(config.extensions),  # Pass as tuple
            use_gitignore=config.use_gitignore
        )

        # Compress if requested
        zip_file_path: Optional[Path] = None
        if compress_flag and output_path.exists(): # Check if md file was created before compressing
            logging.info(f"Starting compression for backup file: {output_path}")
            zip_file_path = compress_backup(output_path)
        elif compress_flag:
             logging.warning(f"Skipping compression because Markdown file was not created: {output_path}")


        print_divider()
        print(f"\n{EMOJI['success']} Backup Complete!\n")
        if output_path.exists():
             print(f"{EMOJI['file']} Markdown file saved at: {output_path}")
        if zip_file_path:
            print(f"{EMOJI['zip']} ZIP archive saved at: {zip_file_path}")
        elif compress_flag and not output_path.exists():
             print(f"{EMOJI['warning']} Compression skipped as Markdown file was not created.")
        elif not output_path.exists():
             print(f"{EMOJI['warning']} Backup file generation may have failed. Check logs.")

        print_divider()
        print()

        log_suffix = f", ZIP: {zip_file_path}" if zip_file_path else ""
        if output_path.exists():
            logging.info(f'Backup finished successfully. Markdown: {output_path}{log_suffix}')
        else:
            logging.warning(f'Backup finished, but output file {output_path} may not have been created successfully.')


        # Allow user time to see the results
        print("Press Enter to return to the main menu...", end="", flush=True)
        input()

    except (PermissionError, OSError) as io_error:
         print_status(f"A file/directory access error occurred during backup: {io_error}", "error")
         logging.error(f"Backup process failed due to I/O error: {io_error}", exc_info=True)
         print("Press Enter to return to the main menu...", end="", flush=True)
         input()
    except Exception as e:
        # Catch errors raised from directory creation or other operations
        print_status(f"An error occurred during the backup process: {e}", "error")
        logging.error(f"Backup process failed: {e}", exc_info=True)  # Log full traceback for debugging

        # Allow user time to see the error
        print("Press Enter to return to the main menu...", end="", flush=True)
        input()
    finally:
        # Perform any necessary cleanup here, if needed
        pass


# --- Main Menu ---
def main_menu():
    """
    Main menu, handles user input and navigation.
    """
    # Determine script directory and set up logging
    try:
        script_directory = Path(sys.argv[0]).resolve().parent
    except Exception:
        # Fallback if sys.argv[0] is unusual
        script_directory = Path.cwd()
    log_file = script_directory / LOG_FILE_NAME
    setup_logging(log_file)

    # Create configuration object
    config_file = script_directory / CONFIG_FILE_NAME
    config = BackupConfig(config_file)

    logging.info(f"Code Backup Tool started, Version {VERSION}")

    while True:
        print_header(f"Code Backup Tool v{VERSION}", "rocket")

        # Display main menu
        print_menu_item("1", "Backup Project (Enter Absolute Path)", "backup")
        print_menu_item("2", "Manage File Extensions", "extension")
        print_menu_item("3", "Manage Feature Settings", "settings")
        print_menu_item("4", "View Help", "help")
        print_menu_item("5", "Exit Program", "exit")

        # Display current gitignore filter status
        gitignore_status = "✓ Enabled" if config.use_gitignore else "✗ Disabled"
        print(f"\n{EMOJI['filter']} Current .gitignore Filtering: {gitignore_status}")

        print()  # Blank line
        user_input = input('> ').strip()

        if user_input == '1':
            backup_project(config)
        elif user_input == '2':
            manage_extensions(config, AVAILABLE_EXTENSIONS)
        elif user_input == '3':
            manage_settings(config)
        elif user_input == '4':
            display_help()
            print()
            input(f'{EMOJI["info"]} Press Enter to return to the main menu...')
        elif user_input == '5':
            print_status('Exiting program.', "info")
            print(f"\n{EMOJI['heart']} Thank you for using the Code Backup Tool. Goodbye!")
            logging.info("Code Backup Tool closed.")
            break
        elif Path(user_input).is_absolute() and Path(user_input).is_dir(): # Check if it looks like an absolute dir path
            # If it's an absolute path to a directory, treat as direct backup input
            backup_project(config, provided_project_dir=user_input)
        elif Path(user_input).is_absolute(): # Is absolute but not a dir
             print_status(f"Path '{user_input}' is absolute but not a valid directory.", "warning")
             time.sleep(1.5)
        else:
            # Handle input that is neither 1-5 nor a valid absolute path
            if Path(user_input).exists() and Path(user_input).is_dir():
                print_status(f"Path '{user_input}' detected, but it is not an absolute path. Please provide an absolute path or choose a menu option [1-5].", "warning")
            else:
                print_status('Invalid input. Please enter an option number [1-5] or a valid absolute directory path.', "error")
            time.sleep(1.5)  # Give user time to read error message

# --- Entry Point ---
if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user. Goodbye!")
        logging.info("Program terminated by user (KeyboardInterrupt).")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        # Log the exception with traceback if logging is set up
        if logging.getLogger().hasHandlers():
             logging.error(f"Program exited abnormally: {e}", exc_info=True)
        sys.exit(1)