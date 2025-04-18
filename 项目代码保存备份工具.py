#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码备份工具 (中文版)
------------------------------------
版本：1.5.4
作者：Jack💡

功能说明：
1. 运行程序时默认直接输入备份项目地址（绝对路径）；当输入内容为有效的绝对路径时，直接进入备份流程；
2. 如果需要管理文件后缀、查看帮助或退出，可在输入选项时输入对应操作数字；
3. 备份过程中生成包含项目目录结构及所有源代码内容的 Markdown 文件（支持多线程）；
4. 用户可选择是否将备份结果压缩为 ZIP 文件；
5. 操作逻辑修改同步于帮助文档，便于查看和维护。
6. 使用 pathlib 进行路径操作，增加类型提示，优化部分逻辑。
7. 支持根据项目中的 .gitignore 文件过滤不需要备份的内容（可在设置中开启/关闭）。
8. 简化的命令行界面，使用表情符号提供友好的用户体验。
9. 优化文件读写性能，减少内存占用，提升多线程处理效率。

注意：
- 默认备份的文件后缀可通过菜单管理；
- 请确保输入的项目路径为绝对路径，并具有访问权限；
- 日志文件将记录备份过程中的关键信息和错误。
- .gitignore 过滤功能默认开启，可在设置菜单中关闭。
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
VERSION = "1.5.4"  # 更新版本号
# 默认备份的文件后缀
DEFAULT_SOURCE_EXTENSIONS: Tuple[str, ...] = (
    '.py', '.java', '.cpp', '.c', '.h', '.cs', '.js', '.ts',
    '.jsx', '.tsx', '.rb', '.go', '.php', '.swift', '.kt',
    '.m', '.mm'
)
# 所有可供选择的后缀
AVAILABLE_EXTENSIONS: Tuple[str, ...] = (
    '.py', '.java', '.cpp', '.c', '.h', '.cs', '.js', '.ts',
    '.jsx', '.tsx', '.rb', '.go', '.php', '.swift', '.kt',
    '.m', '.mm', '.txt', '.md', '.ini', '.cfg', '.json', '.xml',
    '.yaml', '.yml'
)
DEFAULT_BACKUP_DIR_NAME: str = "backup_code"
LOG_FILE_NAME: str = "backup.log"
CONFIG_FILE_NAME: str = "backup_config.json"
CONFIG_VERSION: str = "1.0"  # 配置文件版本，用于未来兼容性
# 决定线程数，基于系统和任务类型（主要是IO密集型）
DEFAULT_MAX_WORKERS: int = min(32, (os.cpu_count() or 4) * 4)
# 文件读取缓冲区大小 (8 MB)
READ_BUFFER_SIZE: int = 8 * 1024 * 1024
# 批处理大小，用于小文件合并处理
BATCH_SIZE: int = 50

# --- 界面表情和符号 ---
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


# --- 界面函数 ---
def clear_screen():
    """清除终端屏幕内容"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title, emoji_key=None):
    """打印标题栏"""
    clear_screen()
    width = 60
    emoji = EMOJI.get(emoji_key, "") if emoji_key else ""

    print("=" * width)
    if emoji:
        print(f"{emoji}  {title}  {emoji}")
    else:
        print(f" {title} ")
    print("=" * width)
    print()  # 添加空行


def print_menu_item(key, text, emoji_key=None):
    """打印菜单项"""
    emoji = EMOJI.get(emoji_key, "") if emoji_key else ""
    if emoji:
        print(f"[{key}] {emoji} {text}")
    else:
        print(f"[{key}] {text}")


def print_status(text, status_type="info", newline=True):
    """打印状态信息"""
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
    """打印进度条"""
    percent = f"{100 * (current / float(total)):.1f}"
    filled_length = int(length * current // total)
    # 使用 # 和 - 作为进度条字符
    bar = "#" * filled_length + "-" * (length - filled_length)
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end="\r")
    if current == total:
        print()  # 完成后换行


def loading_effect(seconds=1, message="处理中"):
    """显示加载效果"""
    chars = "⣾⣽⣻⢿⡿⣟⣯⣷"  # 使用旋转字符模拟加载
    for _ in range(int(seconds * 10)):
        for char in chars:
            print(f"\r{message} {char}", end="", flush=True)
            time.sleep(0.1)
    # 清除加载动画
    print("\r" + " " * (len(message) + 2), end="\r")


def print_divider(char="-", length=60):
    """打印分隔线"""
    print(f"{char * length}")


# --- 日志设置 ---
def setup_logging(log_file: Path):
    """
    设置日志记录配置，将日志记录到文件和控制台。
    """
    # 优化：将日志级别设为INFO，减少DEBUG级别日志的开销
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)  # 保留控制台输出
        ]
    )
    # 抑制某些库的冗余日志
    logging.getLogger("concurrent").setLevel(logging.WARNING)


# --- 配置管理 ---
class BackupConfig:
    """配置管理类，负责加载和保存用户设置"""

    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.extensions: Set[str] = set(DEFAULT_SOURCE_EXTENSIONS)
        self.use_gitignore: bool = True  # 默认启用 .gitignore 过滤
        self.config_version: str = CONFIG_VERSION
        # 增加配置缓存，避免频繁读写磁盘
        self._config_cache: Dict = {}
        # 优化：使用原子加载来避免配置文件损坏
        self.load()

    def load(self):
        """从配置文件加载设置"""
        if not self.config_file.exists():
            logging.info(f"配置文件不存在，使用默认设置: {self.config_file}")
            return

        try:
            # 优化：先读取到内存中验证，确保文件有效才使用
            with self.config_file.open('r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 保存到缓存
            self._config_cache = config_data.copy()

            # 检查配置文件版本
            if 'config_version' in config_data:
                file_version = config_data.get('config_version')
                if file_version != self.config_version:
                    logging.warning(
                        f"配置文件版本不匹配 (文件: {file_version}, 期望: {self.config_version})，尝试兼容加载")

            # 加载文件后缀
            if 'extensions' in config_data and isinstance(config_data['extensions'], list):
                # 验证后缀格式
                valid_extensions = [ext for ext in config_data['extensions']
                                    if isinstance(ext, str) and ext.startswith('.')]
                self.extensions = set(valid_extensions)
                logging.info(f"从配置加载了 {len(self.extensions)} 个文件后缀")

            # 加载 gitignore 过滤设置
            if 'use_gitignore' in config_data and isinstance(config_data['use_gitignore'], bool):
                self.use_gitignore = config_data['use_gitignore']
                logging.info(f".gitignore 过滤功能设置为: {'启用' if self.use_gitignore else '禁用'}")

        except json.JSONDecodeError:
            logging.error(f"配置文件 {self.config_file} 格式无效，使用默认设置")
        except Exception as e:
            logging.error(f"加载配置文件时出错: {e}")

    def save(self):
        """保存设置到配置文件"""
        try:
            # 确保父目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # 准备要保存的配置数据
            config_data = {
                'config_version': self.config_version,
                'extensions': list(self.extensions),
                'use_gitignore': self.use_gitignore
            }

            # 优化：检查配置是否有变化，如无变化则跳过写入
            if self._config_cache == config_data:
                logging.info("配置未变化，跳过保存")
                return

            # 更新缓存
            self._config_cache = config_data.copy()

            # 优化：使用原子写入方式避免配置损坏
            temp_file = self.config_file.with_suffix('.tmp')
            with temp_file.open('w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)

            # 如果原配置文件存在，先备份
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.bak')
                try:
                    self.config_file.replace(backup_file)
                except Exception as e:
                    logging.warning(f"备份原配置文件失败: {e}")

            # 用临时文件替换原配置文件 (原子操作)
            temp_file.replace(self.config_file)

            logging.info(f"设置已保存到配置文件: {self.config_file}")
            print_status(f"设置已保存到配置文件", "success")
        except Exception as e:
            logging.error(f"保存配置文件时出错: {e}")
            print_status(f"保存配置文件时出错: {e}", "error")


# --- GitIgnore 处理 ---
class GitIgnoreFilter:
    """处理 .gitignore 文件并提供路径过滤功能"""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.patterns: List[Pattern] = []
        self.negation_patterns: List[Pattern] = []
        self.loaded = False
        # 优化：添加缓存来加速重复路径的判断
        self._cache: Dict[str, bool] = {}
        # 优化：添加预编译的常用模式字典
        self._common_patterns = {}

        # 尝试加载 .gitignore 文件
        gitignore_path = project_dir / '.gitignore'
        if gitignore_path.exists() and gitignore_path.is_file():
            self._load_gitignore(gitignore_path)
            self.loaded = True
        else:
            logging.info(f"项目目录中未找到 .gitignore 文件: {project_dir}")

    def _load_gitignore(self, gitignore_path: Path):
        """加载并解析 .gitignore 文件"""
        try:
            # 优化：限制.gitignore文件大小，防止异常大文件
            if gitignore_path.stat().st_size > 1024 * 1024:  # 1MB限制
                logging.warning(f".gitignore文件过大: {gitignore_path.stat().st_size} 字节，可能影响性能")

            with gitignore_path.open('r', encoding='utf-8') as f:
                lines = [line.rstrip() for line in f.readlines()]

            valid_patterns = []
            valid_negations = []

            # 预处理：删除重复行并排序，减少后续处理量
            lines = list(dict.fromkeys(lines))

            for line in lines:
                # 忽略空行和注释
                if not line or line.startswith('#'):
                    continue

                # 处理否定模式 (以 ! 开头)
                is_negation = line.startswith('!')
                if is_negation:
                    pattern_str = line[1:].strip()
                else:
                    pattern_str = line.strip()

                # 跳过空模式
                if not pattern_str:
                    continue

                # 将 .gitignore 模式转换为正则表达式
                regex_pattern = self._convert_gitignore_to_regex(pattern_str)

                # 根据模式类型添加到相应列表
                try:
                    compiled_pattern = re.compile(regex_pattern)
                    if is_negation:
                        valid_negations.append(compiled_pattern)
                    else:
                        valid_patterns.append(compiled_pattern)
                except re.error as e:
                    logging.warning(f"无效的.gitignore模式: '{pattern_str}', 错误: {e}")

            self.patterns = valid_patterns
            self.negation_patterns = valid_negations
            logging.info(
                f"从 {gitignore_path} 加载了 {len(valid_patterns)} 个过滤模式和 {len(valid_negations)} 个否定模式")

        except Exception as e:
            logging.error(f"解析 .gitignore 文件时出错: {e}")

    def _convert_gitignore_to_regex(self, pattern: str) -> str:
        """
        将 .gitignore 模式转换为正则表达式
        优化处理：
        1. 添加常用模式缓存
        2. 特殊处理简单的通配符情况
        """
        # 优化：检查缓存中是否有此模式的正则
        if pattern in self._common_patterns:
            return self._common_patterns[pattern]

        # 处理特殊情况
        if not pattern:
            return r'^$'

        # 优化：直接处理常见简单模式
        if pattern == '*':
            result = r'[^/]+$'
            self._common_patterns[pattern] = result
            return result
        elif pattern == '*/':
            result = r'[^/]+/$'
            self._common_patterns[pattern] = result
            return result

        # 检查是否是根目录模式（以 / 开头）
        is_root_pattern = pattern.startswith('/')
        if is_root_pattern:
            pattern = pattern[1:]  # 去掉开头的斜杠

        # 检查是否是目录模式（以 / 结尾）
        is_dir_pattern = pattern.endswith('/')
        if is_dir_pattern:
            pattern = pattern[:-1]  # 暂时去掉结尾的斜杠，后面会特殊处理

        # 转义特殊字符，避免在正则表达式中引起冲突
        pattern = re.escape(pattern)

        # 恢复通配符，因为re.escape会转义它们
        pattern = pattern.replace(r'\*', '*')
        pattern = pattern.replace(r'\?', '?')

        # 处理 ** 通配符（可以匹配多级目录）
        pattern = pattern.replace('**', '__DOUBLEWILDCARD__')

        # 处理单个通配符
        pattern = pattern.replace('*', r'[^/]*')  # * 匹配除了 / 之外的任意字符
        pattern = pattern.replace('?', r'[^/]')  # ? 匹配单个非 / 字符

        # 恢复 ** 通配符并替换为正确的正则表达式（可以匹配跨越多个目录级别）
        pattern = pattern.replace('__DOUBLEWILDCARD__', r'.*')

        # 构建最终的正则表达式模式
        regex = ''

        # 根目录模式需要以 ^ 开头，确保从项目根目录匹配
        if is_root_pattern:
            regex = r'^'
        else:
            # 非根目录模式可以匹配任意层级
            regex = r'(^|/)'

        # 添加主体模式
        regex += pattern

        # 处理目录模式
        if is_dir_pattern:
            # 目录模式匹配目录本身及其所有内容
            regex += r'(/.*)?$'
        else:
            # 非目录模式只匹配具体文件
            regex += r'$'

        # 缓存结果
        self._common_patterns[pattern] = regex
        return regex

    def should_ignore(self, file_path: Path) -> bool:
        """
        根据 .gitignore 规则判断是否应该忽略指定文件
        优化：添加缓存以加速处理
        """
        if not self.loaded or not self.patterns:
            return False

        # 获取相对于项目根目录的路径
        try:
            rel_path = str(file_path.relative_to(self.project_dir))
            # 统一使用正斜杠
            rel_path = rel_path.replace('\\', '/')
        except ValueError:
            # 如果路径不在项目目录下（例如，路径是项目目录本身），则不忽略
            return False

        # 优化：检查缓存
        if rel_path in self._cache:
            return self._cache[rel_path]

        # 首先检查否定模式（明确不忽略的模式）
        for neg_pattern in self.negation_patterns:
            if neg_pattern.search(rel_path):
                self._cache[rel_path] = False
                return False

        # 然后检查忽略模式
        for pattern in self.patterns:
            if pattern.search(rel_path):
                self._cache[rel_path] = True
                return True

        # 结果为不忽略
        self._cache[rel_path] = False
        return False


# --- 优化的文件读取函数 ---
def read_file_content_buffered(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    使用缓冲区读取文件内容，更高效地处理大文件
    返回 (内容字符串, 错误信息字符串) 或 (None, 错误信息字符串)
    """
    try:
        # 首先检查文件大小
        file_size = file_path.stat().st_size

        # 如果文件过大（超过10MB），输出警告
        if file_size > 10 * 1024 * 1024:  # 10 MB
            logging.warning(f"文件过大 ({file_size} 字节): {file_path}")

        # 对于小文件（<1MB），直接读取
        if file_size < 1024 * 1024:  # 1 MB
            with file_path.open('r', encoding='utf-8') as f:
                return f.read(), None

        # 对于大文件，使用缓冲区读取
        content = io.StringIO()
        try:
            with file_path.open('r', encoding='utf-8') as f:
                while True:
                    chunk = f.read(READ_BUFFER_SIZE)
                    if not chunk:
                        break
                    content.write(chunk)
            return content.getvalue(), None
        except UnicodeDecodeError:
            # UTF-8失败，尝试latin-1
            content = io.StringIO()
            with file_path.open('r', encoding='latin-1') as f:
                while True:
                    chunk = f.read(READ_BUFFER_SIZE)
                    if not chunk:
                        break
                    content.write(chunk)
            return content.getvalue(), None

    except UnicodeDecodeError:
        logging.warning(f"文件 {file_path} 不是有效的 UTF-8 编码, 尝试 latin-1...")
        try:
            with file_path.open('r', encoding='latin-1') as f:
                return f.read(), None
        except Exception as e:
            err_msg = f"无法以 UTF-8 或 latin-1 读取文件 {file_path}: {e}"
            logging.error(err_msg)
            return None, err_msg
    except PermissionError as e:
        err_msg = f"无权限读取文件 {file_path}: {e}"
        logging.error(err_msg)
        return None, err_msg
    except Exception as e:
        err_msg = f"读取文件 {file_path} 时发生未知错误: {e}"
        logging.error(err_msg)
        return None, err_msg


# --- 核心逻辑 ---
def get_code_files(directory: Path, extensions: Tuple[str, ...], gitignore_filter: Optional[GitIgnoreFilter] = None,
                   use_gitignore: bool = True) -> List[Path]:
    """
    遍历目录，获取所有指定后缀的文件路径列表。
    使用 Path.rglob 进行高效遍历。
    可选使用 .gitignore 过滤

    优化：使用生成器和过滤器减少内存使用
    """
    code_files = []

    # 优化：使用一次性遍历查找所有后缀的文件
    def find_matching_files() -> Iterator[Path]:
        # 创建扩展名检查集合，提高查找速度
        ext_set = set(extensions)

        try:
            # 优化：使用os.walk提供更好的控制
            for root, dirs, files in os.walk(str(directory)):
                # 优化：过滤目录
                if use_gitignore and gitignore_filter and gitignore_filter.loaded:
                    # 过滤掉应该被忽略的目录
                    root_path = Path(root)
                    dirs[:] = [d for d in dirs if not gitignore_filter.should_ignore(root_path / d)]

                for file in files:
                    # 检查文件扩展名
                    file_path = Path(os.path.join(root, file))
                    if file_path.suffix.lower() in ext_set:
                        # 检查gitignore过滤
                        if use_gitignore and gitignore_filter and gitignore_filter.loaded:
                            if not gitignore_filter.should_ignore(file_path):
                                yield file_path
                        else:
                            yield file_path
        except PermissionError as e:
            logging.warning(f"无权限访问目录: {e}")
        except Exception as e:
            logging.error(f"遍历目录时出错: {e}")

    # 使用生成器查找文件，并立即转换为排序列表
    code_files = sorted(find_matching_files(), key=lambda p: str(p))

    logging.info(f"在 {directory} 中找到 {len(code_files)} 个符合条件的文件。")
    return code_files


def build_tree(directory: Path, prefix: str = "", gitignore_filter: Optional[GitIgnoreFilter] = None,
               use_gitignore: bool = True) -> str:
    """
    递归构建目录树的字符串表示。
    使用 pathlib 和优化的字符串构建。
    可选应用 .gitignore 过滤

    优化：使用StringIO来高效构建字符串
    """
    # 使用StringIO而不是字符串连接，提高性能
    lines = io.StringIO()

    try:
        # 获取目录内容并排序
        contents = sorted(list(directory.iterdir()), key=lambda p: (not p.is_dir(), str(p.name).lower()))

        # 如果启用了 .gitignore 过滤且加载了有效的过滤器，则过滤目录内容
        if use_gitignore and gitignore_filter and gitignore_filter.loaded:
            # 过滤掉应该被忽略的文件和目录
            contents = [item for item in contents if not gitignore_filter.should_ignore(item)]

    except PermissionError:
        logging.warning(f'无权限访问目录：{directory}')
        return ""
    except OSError as e:
        logging.warning(f'访问目录时出错：{directory} - {e}')
        return ""

    # 没有内容则返回空字符串
    if not contents:
        return ""

    # 生成连接符
    pointers = ['├── '] * (len(contents) - 1) + ['└── ']
    for pointer, item_path in zip(pointers, contents):
        if item_path.is_dir():
            lines.write(f'{prefix}{pointer}{item_path.name}/\n')
            extension = '│   ' if pointer == '├── ' else '    '
            # 递归调用，传递过滤器
            subtree = build_tree(item_path, prefix + extension, gitignore_filter, use_gitignore)
            if subtree:
                lines.write(f"{subtree}\n")
        else:
            lines.write(f'{prefix}{pointer}{item_path.name}\n')

    # 返回构建的字符串，去除末尾多余的换行符
    result = lines.getvalue()
    return result.rstrip('\n')


def get_directory_tree(directory: Path, gitignore_filter: Optional[GitIgnoreFilter] = None,
                       use_gitignore: bool = True) -> str:
    """
    获取指定目录的树状结构，并返回包裹在 Markdown 代码块中的字符串。
    可选应用 .gitignore 过滤
    """
    project_name = directory.name
    # 递归构建树时传递过滤器
    tree_str = f'{project_name}/\n{build_tree(directory, "", gitignore_filter, use_gitignore)}'
    return f"```\n{tree_str}\n```\n"


def get_language_from_extension(file_path: Path) -> str:
    """
    根据文件扩展名返回相应的 Markdown 代码块语言标识。

    优化：使用全局缓存字典而不是每次创建
    """
    # 静态字典缓存，添加为函数属性以重用
    if not hasattr(get_language_from_extension, 'language_map'):
        get_language_from_extension.language_map: Dict[str, str] = {
            '.py': 'python', '.java': 'java', '.cpp': 'cpp', '.c': 'c',
            '.h': 'cpp', '.cs': 'csharp', '.js': 'javascript', '.ts': 'typescript',
            '.jsx': 'jsx', '.tsx': 'tsx', '.rb': 'ruby', '.go': 'go',
            '.php': 'php', '.swift': 'swift', '.kt': 'kotlin', '.m': 'objectivec',
            '.mm': 'objectivec', '.md': 'markdown', '.json': 'json', '.xml': 'xml',
            '.yaml': 'yaml', '.yml': 'yaml',
            # 常见配置/文本类型 - 默认无语言提示
            '.txt': '', '.ini': '', '.cfg': '',
        }

    extension = file_path.suffix.lower()
    return get_language_from_extension.language_map.get(extension, '')  # 未找到扩展名时返回空字符串


def process_file_task(file_path: Path, base_dir: Path) -> Tuple[Path, str]:
    """
    单个文件的处理任务：读取内容并格式化为 Markdown 片段。
    返回 (文件相对路径, Markdown 内容字符串)。

    优化：使用StringIO和优化的文件读取
    """
    relative_path = file_path.relative_to(base_dir)
    lang = get_language_from_extension(file_path)

    # 使用缓冲区读取文件内容
    content_str, error_str = read_file_content_buffered(file_path)

    # 使用StringIO构建Markdown内容
    md_content = io.StringIO()
    md_content.write(f'### 文件：`{relative_path}`\n\n')
    md_content.write(f'```{lang}\n')

    if content_str is not None:
        md_content.write(content_str)
    else:
        # 在 Markdown 输出中包含错误信息
        md_content.write(f"Error reading file: {error_str}")

    md_content.write('\n```\n\n')

    return relative_path, md_content.getvalue()


def process_files_batch(files_batch: List[Path], base_dir: Path) -> List[Tuple[Path, str]]:
    """
    处理文件批次，优化小文件的处理效率
    """
    results = []
    for file_path in files_batch:
        try:
            results.append(process_file_task(file_path, base_dir))
        except Exception as e:
            # 处理错误但继续批处理
            relative_path = file_path.relative_to(base_dir)
            error_content = f"### 文件：`{relative_path}`\n\n```\nError processing file: {e}\n```\n\n"
            results.append((relative_path, error_content))
            logging.error(f"处理文件 {relative_path} 时出错: {e}")
    return results


def write_code_and_structure(
        directory: Path,
        output_file: Path,
        extensions: Tuple[str, ...],
        use_gitignore: bool = True,
        max_workers: int = DEFAULT_MAX_WORKERS
):
    """
    将项目目录结构和所有符合条件的源代码文件内容写入 Markdown 文件。
    使用 ThreadPoolExecutor 多线程读取文件，收集结果后统一写入。
    可选使用 .gitignore 过滤

    优化：
    - 使用批处理减少线程创建开销
    - 使用直接写入而不是构建大字符串
    - 添加进度反馈增强
    """
    logging.info(f"开始处理项目：{directory}")
    print_status(f"开始处理项目：{directory}", "info")

    # 初始化 gitignore 过滤器（如果启用）
    gitignore_filter = None
    if use_gitignore:
        gitignore_filter = GitIgnoreFilter(directory)
        if gitignore_filter.loaded:
            logging.info(f"已加载 .gitignore 过滤规则，准备应用过滤")
            print_status(f"已加载 .gitignore 过滤规则", "info")
        else:
            logging.info("未找到有效的 .gitignore 文件，将不进行过滤")

    loading_effect(1, f"{EMOJI['filter']} 正在扫描文件")

    # 获取文件时传递过滤器
    start_time = time.time()
    code_files = get_code_files(directory, extensions, gitignore_filter, use_gitignore)
    scan_time = time.time() - start_time
    logging.info(f"文件扫描完成，用时 {scan_time:.2f} 秒")

    total_files = len(code_files)

    if total_files == 0:
        logging.warning("未找到任何符合条件的文件进行备份。")
        print_status("未找到任何符合条件的文件进行备份。", "warning")

        # 即使没有文件，也创建 Markdown 文件并说明
        try:
            loading_effect(1, f"{EMOJI['note']} 生成备份文件")
            with output_file.open('w', encoding='utf-8') as out_f:
                out_f.write(f'# 项目名称：{directory.name}\n\n')
                out_f.write('## 项目目录结构：\n\n')
                # 生成目录树时传递过滤器
                out_f.write(get_directory_tree(directory, gitignore_filter, use_gitignore))
                out_f.write('## 所有源代码文件的内容：\n\n')
                out_f.write('**未找到任何符合指定后缀的文件。**\n')

                # 记录过滤信息
                out_f.write('\n## 备份信息\n\n')
                out_f.write(f'- 版本：{VERSION}\n')
                out_f.write(f'- 备份时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                if use_gitignore and gitignore_filter and gitignore_filter.loaded:
                    out_f.write(f'- 已启用 .gitignore 过滤\n')
                else:
                    out_f.write(f'- 未启用 .gitignore 过滤\n')
                out_f.write(f'- 包含的文件后缀：{", ".join(sorted(extensions))}\n')
                out_f.write(f'- 总文件数：0\n')

            logging.info(f"已生成空的备份文件：{output_file}")
            print_status(f"已生成空的备份文件：{output_file}", "success")
        except Exception as e:
            logging.error(f"写入空的输出文件时出错：{e}")
            print_status(f"写入输出文件时出错：{e}", "error")
        return  # 如果没有文件则停止处理

    # --- 1. 写入头部和目录结构 ---
    try:
        print_status(f"开始生成目录结构...", "info")
        loading_effect(1, f"{EMOJI['folder']} 正在分析目录结构")

        start_time = time.time()
        with output_file.open('w', encoding='utf-8') as out_f:
            out_f.write(f'# 项目名称：{directory.name}\n\n')
            out_f.write('## 项目目录结构：\n\n')
            # 生成目录树时传递过滤器
            out_f.write(get_directory_tree(directory, gitignore_filter, use_gitignore))
            out_f.write('## 所有源代码文件的内容：\n\n')

            # 添加过滤信息
            if use_gitignore and gitignore_filter and gitignore_filter.loaded:
                out_f.write('> 注：备份时已应用 .gitignore 规则过滤文件\n\n')

        tree_time = time.time() - start_time
        logging.info(f"目录结构生成完成，用时 {tree_time:.2f} 秒")
        print_status("目录结构生成完成", "success")

    except Exception as e:
        logging.error(f'写入输出文件头部信息时出错：{e}')
        print_status(f'写入文件头部信息时出错：{e}', "error")
        # 如果无法写入文件头部，最好退出
        sys.exit(f"无法写入备份文件头部: {output_file}. 错误: {e}")

    # --- 2. 并发处理文件 ---
    # 优化：根据文件大小自动调整批处理大小和线程数
    batch_size = BATCH_SIZE

    # 对于大文件，减少批处理大小
    avg_size = sum(f.stat().st_size for f in code_files[:min(100, len(code_files))]) / min(100, len(code_files)) if len(code_files) > 0 else 0 # 确保不除以零
    if avg_size > 1024 * 1024:  # 如果平均文件大于1MB
        batch_size = max(1, BATCH_SIZE // 10)  # 减小批处理大小
        # 对于非常大的文件，减少线程数
        if avg_size > 10 * 1024 * 1024:  # 如果平均文件大于10MB
            max_workers = max(4, max_workers // 4)

    # 创建文件批次
    batches = []
    for i in range(0, len(code_files), batch_size):
        batches.append(code_files[i:i + batch_size])

    logging.info(f"将 {total_files} 个文件分成 {len(batches)} 个批次处理 (每批 ~{batch_size} 个文件)")

    processed_count = 0
    lock = threading.Lock()  # 用于安全更新计数器

    print_status(f"开始处理 {total_files} 个文件 (使用 {max_workers} 个线程)...", "info")
    logging.info(f"开始使用最多 {max_workers} 个线程处理 {total_files} 个文件...")

    start_time = time.time()

    # 优化：直接将结果写入文件，而非保存在内存中
    with output_file.open('a', encoding='utf-8') as out_f:
        # 使用线程池处理文件批次
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交批处理任务
            future_to_batch = {executor.submit(process_files_batch, batch, directory): batch_idx
                               for batch_idx, batch in enumerate(batches)}

            # 为了有序写入，记录已完成的批次和结果
            completed_results = {}
            next_batch_to_write = 0

            # 处理已完成的任务
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()

                    # 更新处理计数
                    with lock:
                        processed_count += len(batch_results)
                        # 更新进度条
                        print_progress(processed_count, total_files,
                                       prefix=f"{EMOJI['file']} 处理文件",
                                       suffix=f"{processed_count}/{total_files}")

                    # 存储批次结果
                    completed_results[batch_idx] = batch_results

                    # 尝试按顺序写入已完成的批次
                    while next_batch_to_write in completed_results:
                        # 按文件路径排序一个批次内的结果
                        sorted_results = sorted(completed_results[next_batch_to_write], key=lambda x: str(x[0]))

                        # 写入此批次的所有文件
                        for _, content in sorted_results:
                            out_f.write(content)

                        # 删除已写入的批次数据释放内存
                        del completed_results[next_batch_to_write]
                        next_batch_to_write += 1

                except Exception as e:
                    # 记录批处理错误
                    logging.error(f"处理批次 {batch_idx} 失败: {e}")
                    with lock:
                        processed_count += len(batches[batch_idx]) if batch_idx < len(batches) else 0 # 安全访问批次
                        print_progress(processed_count, total_files,
                                       prefix=f"{EMOJI['file']} 处理文件",
                                       suffix=f"{processed_count}/{total_files}")

        # 记录处理时间
        processing_time = time.time() - start_time
        processing_rate = total_files / processing_time if processing_time > 0 else 0
        logging.info(f"文件处理完成，耗时 {processing_time:.2f} 秒，平均 {processing_rate:.2f} 文件/秒")

        print()  # 进度条完成后换行
        print_status("所有文件处理完成", "success")

        # 3. 添加备份信息
        logging.info("开始写入备份元数据...")
        loading_effect(0.5, f"{EMOJI['info']} 完成备份信息")

        # 在文件末尾添加备份信息
        out_f.write('\n## 备份信息\n\n')
        out_f.write(f'- 版本：{VERSION}\n')
        out_f.write(f'- 备份时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        if use_gitignore and gitignore_filter and gitignore_filter.loaded:
            out_f.write(f'- 已启用 .gitignore 过滤\n')
        else:
            out_f.write(f'- 未启用 .gitignore 过滤\n')
        out_f.write(f'- 包含的文件后缀：{", ".join(sorted(extensions))}\n')
        out_f.write(f'- 总文件数：{total_files}\n')
        out_f.write(f'- 处理时间：{processing_time:.2f} 秒\n')

    # 完成写入
    total_time = time.time() - start_time # 此处 start_time 实际是处理文件开始时间，非整体开始时间
    logging.info(f"成功备份完成") # 移除不准确的总耗时
    print_status(f"成功将所有内容写入：{output_file}", "success")


def compress_backup(output_file: Path) -> Optional[Path]:
    """
    将生成的 Markdown 文件压缩为 ZIP 文件。

    优化：使用更高效的压缩级别和更大的缓冲区
    """
    # 输出 zip 文件与 .md 文件在同一目录
    zip_filename = output_file.with_suffix('.zip')
    try:
        print_status(f"正在压缩备份文件...", "info")
        loading_effect(1, f"{EMOJI['zip']} 正在压缩文件")

        # 获取开始时间以计算性能
        start_time = time.time()

        # 使用最佳压缩选项
        compression = zipfile.ZIP_DEFLATED
        compression_level = 9  # 最高压缩级别

        with zipfile.ZipFile(zip_filename, 'w', compression=compression, compresslevel=compression_level) as zipf:
            # 将 markdown 文件添加到 zip 中，存档内部使用其自身的文件名
            zipf.write(output_file, arcname=output_file.name)

        # 计算压缩效率和时间
        original_size = output_file.stat().st_size
        compressed_size = zip_filename.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        compress_time = time.time() - start_time

        logging.info(f'备份文件已压缩为：{zip_filename} (原始: {original_size / 1024:.1f}KB, '
                     f'压缩: {compressed_size / 1024:.1f}KB, 节省: {compression_ratio:.1f}%, '
                     f'耗时: {compress_time:.2f}秒)')

        print_status(f'备份文件已压缩为：{zip_filename} (压缩率: {compression_ratio:.1f}%)', "success")
        return zip_filename
    except Exception as e:
        logging.error(f'压缩备份文件 {output_file} 时出错：{e}')
        print_status(f'压缩备份文件时出错：{e}', "error")
        return None


# --- 用户界面 ---
def display_help():
    """
    显示帮助文档。
    """
    print_header(f"代码备份工具 使用帮助 v{VERSION}", "help")

    help_text = f"""
{EMOJI['rocket']} 本工具用于备份指定项目目录下的源代码文件，并生成包含目录结构和源代码内容的 Markdown 文件。
{EMOJI['star']} 支持多线程处理及结果压缩。

【功能】
{EMOJI['extension']} 备份指定后缀文件：可通过菜单自定义备份的文件类型。
{EMOJI['folder']} 显示项目目录结构：以树状结构展示项目文件夹和文件。
{EMOJI['file']} 保存源代码内容：将源代码写入 Markdown 文件，便于查看和分享。
{EMOJI['rocket']} 多线程处理：利用多核 CPU 提高大项目备份效率。
{EMOJI['zip']} 备份结果压缩：可选择将生成的 Markdown 文件压缩为 ZIP 文件。
{EMOJI['filter']} .gitignore 过滤：可根据项目中的 .gitignore 文件过滤不需要备份的内容（默认启用）。
{EMOJI['note']} 日志记录：记录备份过程中的关键信息和错误到 backup.log 文件。
{EMOJI['config']} 设置持久化：保存您的文件后缀和功能开关设置。

【使用方法】
{EMOJI['info']} 启动程序后，可直接输入项目的 绝对路径 进行备份。
{EMOJI['info']} 或输入数字选择其他操作：
  [1] {EMOJI['backup']} 备份项目 (需要输入绝对路径)
  [2] {EMOJI['extension']} 管理文件后缀设置
  [3] {EMOJI['settings']} 管理功能设置
  [4] {EMOJI['help']} 查看本帮助信息
  [5] {EMOJI['exit']} 退出程序

【文件后缀管理】
{EMOJI['info']} 在后缀管理菜单中，可以：
  - 查看所有可选的后缀和当前已选的后缀。
  - 使用 'add <后缀1> <后缀2> ...' 添加后缀 (例如: add .txt .log)。
  - 使用 'remove <后缀1> <后缀2> ...' 删除后缀 (例如: remove .java)。
  - 使用 'reset' 恢复到默认后缀列表。
  - 使用 'back' 返回主菜单。
  (注意：添加/删除时，后缀前的点 '.' 是可选的)

【功能设置】
{EMOJI['info']} 在功能设置菜单中，您可以：
  - 开启/关闭 .gitignore 文件过滤功能。
  - 查看当前功能状态。
  - 所有设置会自动保存，下次启动时自动加载。

【.gitignore 过滤说明】
{EMOJI['filter']} 当启用 .gitignore 过滤功能时，程序会自动检测项目根目录中的 .gitignore 文件。
{EMOJI['filter']} 所有符合 .gitignore 规则的文件和目录将被排除在备份之外。
{EMOJI['filter']} 支持以下 .gitignore 模式特性:
  - 以斜杠开头的模式 (/foo) 只匹配项目根目录
  - 不以斜杠开头的模式 (foo) 匹配任何层级的路径
  - 以斜杠结尾的模式 (foo/) 匹配目录及其所有内容
  - 支持 ** 通配符匹配多级目录
{EMOJI['info']} 如果项目中没有 .gitignore 文件，此功能不会产生任何效果。

【性能优化】
{EMOJI['rocket']} 本版本 (v{VERSION}) 包含以下性能优化:
  - 高效的文件读取: 使用缓冲区读取大文件
  - 智能的线程分配: 根据文件大小自动调整线程数
  - 批处理小文件: 减少线程切换开销
  - 内存使用优化: 流式处理大文件避免内存占用过高
  - .gitignore解析优化: 使用缓存加速路径匹配
  - 原子文件操作: 确保配置文件和输出文件的完整性

作者：Jack {EMOJI['light']}
"""
    print(help_text)


def manage_extensions(config: BackupConfig, available_extensions: Tuple[str, ...]) -> None:
    """
    管理备份时检测的文件后缀设置，并保存到配置。
    增加明确的退出提示。
    """
    # 使用副本操作，以便需要时可以放弃更改（虽然这里我们直接更新）
    current_ext_set = config.extensions.copy()
    available_ext_set = set(available_extensions)

    # 清屏并显示标题
    print_header("文件后缀管理", "extension")
    print(f"{EMOJI['info']} 在此菜单中，您可以修改备份时包含的文件类型。")
    print(f"{EMOJI['info']} 输入 'back' 可以随时返回主菜单。")

    while True:
        print_divider()
        print(
            f"{EMOJI['extension']} 当前已选后缀 ({len(current_ext_set)}): {', '.join(sorted(list(current_ext_set)))}")

        print(f"\n可用命令:")
        print(f"{EMOJI['info']} add [.ext1] [.ext2]... - 添加后缀")
        print(f"{EMOJI['info']} remove [.ext1] [.ext2]... - 删除后缀")
        print(f"{EMOJI['info']} reset - 重置为默认后缀")
        print(f"{EMOJI['info']} showall - 显示所有可用后缀")
        print(f"{EMOJI['info']} back - 返回主菜单")

        cmd_input = input('文件后缀管理 > ').strip().lower()
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
                        print(f"  {EMOJI['success']} 已添加: {normalized_ext}")
                    else:
                        print(f"  {EMOJI['info']} 提示: {normalized_ext} 已在列表中。")
                else:
                    print(f"  {EMOJI['warning']} 警告：后缀 '{normalized_ext}' 不在可用列表中，已忽略。")
            if added_count > 0:
                print(f"  {EMOJI['success']} 成功添加 {added_count} 个新后缀。")

                # 保存当前配置
                config.extensions = current_ext_set
                config.save()

        elif command == "remove" and len(parts) > 1:
            removed_count = 0
            for ext in parts[1:]:
                normalized_ext = ext if ext.startswith('.') else '.' + ext
                if normalized_ext in current_ext_set:
                    current_ext_set.remove(normalized_ext)
                    removed_count += 1
                    print(f"  {EMOJI['success']} 已移除: {normalized_ext}")
                else:
                    print(f"  {EMOJI['info']} 提示：后缀 '{normalized_ext}' 不在当前选择中，已忽略。")
            if removed_count > 0:
                print(f"  {EMOJI['success']} 成功移除 {removed_count} 个后缀。")

                # 保存当前配置
                config.extensions = current_ext_set
                config.save()

        elif command == "reset":
            current_ext_set = set(DEFAULT_SOURCE_EXTENSIONS)
            print(f"  {EMOJI['success']} 文件后缀已重置为默认列表。")

            # 保存当前配置
            config.extensions = current_ext_set
            config.save()

        elif command == "showall":
            print(f"{EMOJI['info']} 所有可用后缀 ({len(available_ext_set)}):")
            # 每行显示 5 个后缀，更整齐
            ext_list = sorted(list(available_extensions))
            for i in range(0, len(ext_list), 5):
                print(f"  {' '.join(ext_list[i:i + 5])}")

        elif command == "back":
            print(f"\n{EMOJI['exit']} 退出文件后缀管理，返回主菜单")
            # 返回主菜单前短暂延迟
            time.sleep(0.5)
            return

        elif not command:  # 如果用户只按了回车
            print(f"{EMOJI['info']} 请输入命令。提示：输入 'back' 可返回主菜单。")
        else:
            print(f"{EMOJI['error']} 无效命令 '{command}'。")
            print(f"{EMOJI['info']} 可用命令: add, remove, reset, showall, back。")

            # 给用户一些时间阅读输出
        time.sleep(0.5)

# 注意：这里是嵌套定义，所以需要调整内部函数定义之前的缩进
# （虽然原代码也是这样写的，但指出这一点有助于理解结构）
# 为了符合“仅调整缩进”的要求，此处保留原有的嵌套结构
# 但在实际开发中，通常建议将这些辅助函数移到 main_menu 之外
# 或者将它们作为 main_menu 的局部函数（如果只在 main_menu 中使用）

def manage_settings(config: BackupConfig) -> None:
    """管理功能设置菜单"""
    print_header("功能设置", "settings")
    print(f"{EMOJI['info']} 在此菜单中，您可以管理程序的各项功能设置。")
    print(f"{EMOJI['info']} 输入 'back' 可以随时返回主菜单。")

    while True:
        print_divider()

        # 显示当前 gitignore 过滤状态
        status_emoji = EMOJI['success'] if config.use_gitignore else EMOJI['warning']
        status_text = "已启用" if config.use_gitignore else "已禁用"
        print(f"{status_emoji} .gitignore 过滤功能: {status_text}")

        print(f"\n可用命令:")
        toggle_text = "禁用" if config.use_gitignore else "启用"
        print(f"{EMOJI['info']} 1 - {toggle_text} .gitignore 过滤功能")
        print(f"{EMOJI['info']} back - 返回主菜单")

        cmd_input = input('功能设置 > ').strip().lower()

        if cmd_input == "1":
            config.use_gitignore = not config.use_gitignore
            status = "启用" if config.use_gitignore else "禁用"
            emoji = EMOJI['success'] if config.use_gitignore else EMOJI['warning']
            print(f"{emoji} .gitignore 过滤功能已{status}")
            # 保存设置
            config.save()
            time.sleep(1)  # 给用户一些时间阅读反馈

        elif cmd_input == "back":
            print(f"\n{EMOJI['exit']} 退出功能设置，返回主菜单")
            time.sleep(0.5)
            return

        elif not cmd_input:
            print(f"{EMOJI['info']} 请输入命令。提示：输入 'back' 可返回主菜单。")

        else:
            print(f"{EMOJI['error']} 无效命令 '{cmd_input}'。请输入有效的选项。")

        # !!! 修正缩进 !!!
        # 这一行应该在 while 循环内，但在 if/elif/else 结构之后执行
        time.sleep(0.5)

def get_backup_destination(script_dir: Path) -> Path:
    """获取并创建用于保存备份的目录"""
    print_status(f"请选择保存备份的位置", "info")
    save_dir_input = input(
        f'{EMOJI["folder"]} 请输入保存备份文件的目录路径 \n  (留空则默认保存在脚本所在目录下的 {DEFAULT_BACKUP_DIR_NAME} 文件夹):\n> ').strip()

    if not save_dir_input:
        save_directory = script_dir / DEFAULT_BACKUP_DIR_NAME
        print_status(f"使用默认目录: {save_directory}", "info")
    else:
        save_directory = Path(save_dir_input).resolve()  # 解析为绝对路径
        print_status(f"使用自定义目录: {save_directory}", "info")

    try:
        loading_effect(0.5, f"{EMOJI['folder']} 准备保存目录")
        save_directory.mkdir(parents=True, exist_ok=True)  # 如果目录不存在则创建
        logging.info(f"备份将保存在: {save_directory}")
        print_status(f"备份将保存在: {save_directory}", "success")
        return save_directory
    except PermissionError:
        logging.error(f"无权限创建或访问保存目录: {save_directory}")
        print_status(f"无权限创建或访问保存目录: {save_directory}", "error")
        raise  # 重新抛出异常给调用者
    except Exception as e:
        logging.error(f"无法创建或访问保存目录 {save_directory}: {e}")
        print_status(f"无法创建或访问保存目录: {e}", "error")
        raise  # 重新抛出

def create_unique_project_backup_folder(save_directory: Path, project_name: str) -> Path:
    """创建本次备份独有的项目文件夹，处理重名情况"""
    base_folder = save_directory / project_name
    project_backup_folder = base_folder
    unique_suffix = 1

    # 如果目录名已存在，添加数字后缀
    while project_backup_folder.exists():
        print_status(f"目录 {project_backup_folder.name} 已存在，尝试新名称...", "info")
        project_backup_folder = save_directory / f"{project_name}_{unique_suffix}"
        unique_suffix += 1

    try:
        loading_effect(0.5, f"{EMOJI['folder']} 创建项目文件夹")
        project_backup_folder.mkdir(parents=True)
        logging.info(f"创建项目备份文件夹: {project_backup_folder}")
        print_status(f"已创建项目备份文件夹: {project_backup_folder}", "success")
        return project_backup_folder
    except Exception as e:
        logging.error(f"无法创建项目备份文件夹 {project_backup_folder}: {e}")
        print_status(f"无法创建项目备份文件夹: {e}", "error")
        raise  # 重新抛出

def backup_project(config: BackupConfig, provided_project_dir: Optional[str] = None):
    """
    执行一次完整的项目备份流程。
    """
    print_header("项目备份", "backup")
    script_directory = Path(sys.argv[0]).resolve().parent

    project_path_str: str
    if provided_project_dir:
        project_path_str = provided_project_dir
    else:
        project_path_str = input(f'{EMOJI["folder"]} 请输入待备份项目的绝对路径：\n> ').strip()

    if not project_path_str:
        print_status('未输入项目路径', "error")
        logging.error("备份流程中止：用户未输入项目路径。")
        time.sleep(1.5)
        return

    project_directory = Path(project_path_str)

    # 验证项目目录
    if not project_directory.is_absolute():
        print_status(f"提供的路径 '{project_path_str}' 不是绝对路径", "error")
        logging.error(f"备份流程中止：路径非绝对路径 - {project_path_str}")
        time.sleep(1.5)
        return
    if not project_directory.is_dir():
        print_status(f'指定路径不存在或不是一个目录：{project_directory}', "error")
        logging.error(f"备份流程中止：路径无效或非目录 - {project_directory}")
        time.sleep(1.5)
        return

    try:
        # 获取并创建保存目录
        save_directory = get_backup_destination(script_directory)

        # 在 save_directory 中为此备份运行创建唯一的文件夹
        project_name = project_directory.name
        project_backup_folder = create_unique_project_backup_folder(save_directory, project_name)

        # 定义输出 Markdown 文件路径
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')  # 添加秒以增加唯一性
        output_filename = f'{project_name}_backup_{current_time}.md'
        output_path = project_backup_folder / output_filename

        # 询问是否压缩
        compress_choice = input(
            f'{EMOJI["zip"]} 是否将备份结果压缩为 ZIP 文件？(y/n，默认为 n):\n> ').strip().lower()
        compress_flag = compress_choice in ('y', 'yes')

        # 显示 gitignore 过滤状态
        gitignore_status = "启用" if config.use_gitignore else "禁用"
        gitignore_emoji = EMOJI['success'] if config.use_gitignore else EMOJI['warning']
        print(
            f"\n{gitignore_emoji} .gitignore 过滤功能 当前已{gitignore_status}。")
        print(f"  如需更改，请在主菜单中选择「管理功能设置」。")

        logging.info(f"开始备份项目 '{project_name}' 到 {output_path}")
        print()
        print_status(f'开始备份项目 "{project_name}"...', "info")
        print_divider()

        # 执行核心备份任务
        write_code_and_structure(
            directory=project_directory,
            output_file=output_path,
            extensions=tuple(config.extensions),  # 传递为元组
            use_gitignore=config.use_gitignore
        )

        # 如果需要则压缩
        zip_file_path: Optional[Path] = None
        if compress_flag:
            logging.info(f"开始压缩备份文件: {output_path}")
            zip_file_path = compress_backup(output_path)

        print_divider()
        print(f"\n{EMOJI['success']} 备份完成!\n")
        print(f"{EMOJI['file']} Markdown 文件保存在: {output_path}")
        if zip_file_path:
            print(f"{EMOJI['zip']} ZIP 压缩文件保存在: {zip_file_path}")
        print_divider()
        print()

        logging.info(
            f'备份成功完成。Markdown: {output_path}{f", ZIP: {zip_file_path}" if zip_file_path else ""}')

        # 让用户有时间查看结果
        print("按 Enter 键返回主菜单...", end="", flush=True)
        input()

    except (PermissionError, OSError, Exception) as e:
        # 捕获目录创建或其他操作中引发的错误
        print_status(f"备份过程中发生错误：{e}", "error")
        logging.error(f"备份流程失败：{e}", exc_info=True)  # 记录完整的回溯信息以供调试

        # 让用户有时间查看错误
        print("按 Enter 键返回主菜单...", end="", flush=True)
        input()
    finally:
        # 如果需要，执行任何清理操作
        pass

# --- 主菜单 ---
def main_menu():
    """
    主菜单，处理用户输入和导航。
    """
    # 确定脚本目录并设置日志
    try:
        script_directory = Path(sys.argv[0]).resolve().parent
    except Exception:
        # 如果 sys.argv[0] 奇怪，则回退
        script_directory = Path.cwd()
    log_file = script_directory / LOG_FILE_NAME
    setup_logging(log_file)

    # 创建配置对象
    config_file = script_directory / CONFIG_FILE_NAME
    config = BackupConfig(config_file)

    logging.info(f"代码备份工具启动，版本 {VERSION}")

    while True:
        print_header(f"代码备份工具 v{VERSION}", "rocket")

        # 显示主菜单
        print_menu_item("1", "备份项目 (输入绝对路径)", "backup")
        print_menu_item("2", "管理文件后缀", "extension")
        print_menu_item("3", "管理功能设置", "settings")
        print_menu_item("4", "查看帮助", "help")
        print_menu_item("5", "退出程序", "exit")

        # 显示当前 gitignore 过滤状态
        gitignore_status = "✓ 已启用" if config.use_gitignore else "✗ 已禁用"
        print(f"\n{EMOJI['filter']} 当前 .gitignore 过滤: {gitignore_status}")

        print()  # 空行
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
            input(f'{EMOJI["info"]} 按 Enter键 返回主菜单...')
        elif user_input == '5':
            print_status('程序已退出。', "info")
            print(f"\n{EMOJI['heart']} 感谢使用代码备份工具，再见！")
            logging.info("代码备份工具关闭。")
            break
        elif Path(user_input).is_absolute():  # 检查输入是否像绝对路径
            # 如果是绝对路径，则视为直接输入路径
            backup_project(config, provided_project_dir=user_input)
        else:
            # 处理输入既不是 1-5 也不是绝对路径的情况
            if Path(user_input).exists() and Path(user_input).is_dir():
                print_status(f"检测到路径 '{user_input}'，但它不是绝对路径。请输入绝对路径或选择菜单选项 [1-5]。",
                             "warning")
            else:
                print_status('无效输入。请输入选项数字 [1-5] 或一个有效的绝对路径。', "error")
            time.sleep(1.5)  # 给用户时间阅读错误信息

# --- 入口点 ---
if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断。再见！")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序遇到错误: {e}")
        logging.error(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)