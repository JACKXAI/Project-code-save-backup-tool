import os
import sys
import threading
import logging
import zipfile
from datetime import datetime

def setup_logging(log_file):
    """
    设置日志记录配置。
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_code_files(directory, extensions):
    """
    遍历目录，获取指定后缀的文件列表。
    """
    code_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            # 判断文件是否为指定的源代码文件
            if file.endswith(extensions):
                file_path = os.path.join(root, file)
                code_files.append(file_path)
    return code_files

def get_directory_tree(directory):
    """
    获取目录的树状结构字符串。
    """
    tree_str = ''
    prefix = ''
    # 获取项目根目录名称
    project_name = os.path.basename(os.path.abspath(directory))
    tree_str += f'{project_name}/\n'
    tree_str += build_tree(directory, prefix)
    return '```\n' + tree_str + '```\n'

def build_tree(directory, prefix):
    """
    递归构建目录树字符串。
    """
    tree_str = ''
    try:
        contents = os.listdir(directory)
    except PermissionError:
        logging.warning(f'无权限访问目录：{directory}')
        return tree_str  # 无权限访问的目录，跳过
    contents = sorted(contents, key=lambda s: s.lower())
    pointers = ['├── '] * (len(contents) - 1) + ['└── '] if contents else []
    for pointer, item in zip(pointers, contents):
        path = os.path.join(directory, item)
        if os.path.isdir(path):
            tree_str += f'{prefix}{pointer}{item}/\n'
            extension = '│   ' if pointer == '├── ' else '    '
            tree_str += build_tree(path, prefix + extension)
        else:
            tree_str += f'{prefix}{pointer}{item}\n'
    return tree_str

def get_language_from_extension(file_path):
    """
    根据文件扩展名，返回对应的语言类型。
    """
    extension = os.path.splitext(file_path)[1].lower()
    language_map = {
        '.py': 'python',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'cpp',
        '.cs': 'csharp',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascriptreact',
        '.tsx': 'typescriptreact',
        '.rb': 'ruby',
        '.go': 'go',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.m': 'objective-c',
        '.mm': 'objective-c',
        '.txt': '',
        '.md': 'markdown',
        '.ini': '',
        '.cfg': '',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
    }
    return language_map.get(extension, '')

def write_code_and_structure(directory, output_file, extensions):
    """
    将目录结构和源代码文件内容写入Markdown文件。
    """
    code_files = get_code_files(directory, extensions)
    total_files = len(code_files)
    processed_files = 0

    # 创建锁对象，用于多线程写入时的线程安全
    write_lock = threading.Lock()

    try:
        with open(output_file, 'w', encoding='utf-8') as out_file:
            # 写入项目名称
            project_name = os.path.basename(os.path.abspath(directory))
            out_file.write(f'# 项目名称：{project_name}\n\n')

            # 写入项目目录结构
            out_file.write('## 项目目录结构：\n\n')
            tree_structure = get_directory_tree(directory)
            out_file.write(tree_structure)
            out_file.write('\n')

            # 写入所有源代码文件的内容
            out_file.write('## 所有源代码文件的内容：\n\n')

        # 定义线程任务
        def process_file(file_path):
            nonlocal processed_files
            relative_path = os.path.relpath(file_path, directory)
            content = ''
            content += f'### 文件：{relative_path}\n\n'
            content += '```{0}\n'.format(get_language_from_extension(file_path))
            try:
                with open(file_path, 'r', encoding='utf-8') as code_file:
                    content += code_file.read()
                content += '\n```\n\n'
            except UnicodeDecodeError:
                # 尝试使用其他编码读取
                try:
                    with open(file_path, 'r', encoding='latin-1') as code_file:
                        content += code_file.read()
                    content += '\n```\n\n'
                except Exception as e:
                    error_msg = f'无法读取文件 {relative_path}，错误信息：{e}'
                    logging.error(error_msg)
                    content += f'{error_msg}\n```\n\n'
            except Exception as e:
                error_msg = f'处理文件 {relative_path} 时发生错误：{e}'
                logging.error(error_msg)
                content += f'{error_msg}\n```\n\n'

            with write_lock:
                with open(output_file, 'a', encoding='utf-8') as out_file:
                    out_file.write(content)
                processed_files += 1
                logging.info(f'已处理文件：{relative_path} ({processed_files}/{total_files})')

        # 使用多线程处理文件
        threads = []
        for file_path in code_files:
            thread = threading.Thread(target=process_file, args=(file_path,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

    except Exception as e:
        logging.error(f'写入输出文件时发生错误：{e}')
        sys.exit(1)

def compress_backup(output_file):
    """
    压缩备份生成的Markdown文件。
    """
    zip_filename = output_file.rstrip('.md') + '.zip'
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(output_file, arcname=os.path.basename(output_file))
        logging.info(f'备份文件已压缩为：{zip_filename}')
        return zip_filename
    except Exception as e:
        logging.error(f'压缩备份文件时发生错误：{e}')

def display_help():
    """
    显示帮助文档。
    """
    help_text = """
====================================
代码备份工具 使用帮助
版本：1.3.0
由Jack编写与制作:)
====================================

本工具用于备份指定项目目录下的源代码文件，并生成包含目录结构和源代码内容的Markdown文件，支持多线程处理和结果压缩。

**功能：**
- 备份指定后缀的文件：可以自定义要备份的文件后缀名。
- 显示项目目录结构：以树状结构展示项目文件和文件夹。
- 保存源代码内容：将源代码文件的内容保存到Markdown文件，便于查看和分享。
- 多线程处理：提高大项目备份的效率。
- 压缩备份结果：可选择是否将生成的Markdown文件压缩为zip文件（默认不压缩）。
- 日志记录：记录备份过程中的重要信息和错误，便于调试和追踪。
- 查看帮助文档：提供详细的使用说明和功能介绍。

**使用方法：**
1. **启动程序**：运行脚本，程序将显示操作命令提示。
2. **输入操作命令**：
   - 输入 `set` 或 `s`：进入文件后缀设置界面。
   - 输入 `help` 或 `h`：显示帮助文档。
   - 输入 `exit` 或 `0`：退出程序。
   - 按回车或输入其他内容：开始备份流程。
3. **文件后缀设置界面**：
   - 显示当前可选的文件后缀类型。
   - 显示已选择的文件后缀类型。
   - 输入 `add` 或 `a`：添加新的文件后缀。
   - 输入 `remove` 或 `r`：删除已选择的文件后缀。
   - 输入 `back` 或 `b`：返回主菜单。
4. **开始备份**：
   - 按提示输入项目路径和保存备份文件的路径。
   - 选择是否压缩备份结果。
   - 程序将自动备份指定类型的源代码文件，并生成Markdown文件。
5. **查看备份结果**：
   - 备份完成后，生成的Markdown文件和压缩的zip文件（如果选择压缩）将保存在指定的目录中。
   - 可以查看日志文件 `backup.log` 查看详细的备份过程信息。

**注意事项：**
- **默认支持的文件后缀名**：`.py`, `.java`, `.cpp`, `.c`, `.h`, `.cs`, `.js`, `.ts`, `.jsx`, `.tsx`, `.rb`, `.go`, `.php`, `.swift`, `.kt`, `.m`, `.mm`, `.txt`, `.md`, `.ini`, `.cfg`, `.json`, `.xml`, `.yaml`, `.yml`。
- **路径输入**：请确保输入的路径为有效的绝对路径。
- **权限**：确保程序有权限访问指定的目录和文件。
- **日志文件**：日志记录保存在脚本所在目录下的 `backup.log` 文件中。

====================================
"""
    print(help_text)

def manage_extensions(source_extensions, available_extensions):
    """
    管理文件后缀设置的界面。
    """
    while True:
        print('\n*** 文件后缀设置 ***')
        print('可选的文件后缀类型：')
        print(', '.join(available_extensions))
        print('\n已选择的文件后缀类型：')
        print(', '.join(source_extensions))
        print('\n操作命令：')
        print('[add/a 添加后缀] [remove/r 删除后缀] [back/b 返回主菜单]')
        cmd = input('> ').strip().lower()
        if cmd in ('add', 'a'):
            print('请输入要添加的文件后缀名，以逗号分隔（例如：.py,.txt）：')
            extensions_input = input('> ').strip()
            if extensions_input:
                extensions_list = [ext.strip() if ext.strip().startswith('.') else '.' + ext.strip() for ext in extensions_input.split(',')]
                for ext in extensions_list:
                    if ext in available_extensions and ext not in source_extensions:
                        source_extensions.append(ext)
                print('已更新已选择的文件后缀类型：')
                print(', '.join(source_extensions))
            else:
                print('未添加任何后缀。')
        elif cmd in ('remove', 'r'):
            print('请输入要删除的文件后缀名，以逗号分隔：')
            extensions_input = input('> ').strip()
            if extensions_input:
                extensions_list = [ext.strip() if ext.strip().startswith('.') else '.' + ext.strip() for ext in extensions_input.split(',')]
                for ext in extensions_list:
                    if ext in source_extensions:
                        source_extensions.remove(ext)
                print('已更新已选择的文件后缀类型：')
                print(', '.join(source_extensions))
            else:
                print('未删除任何后缀。')
        elif cmd in ('back', 'b'):
            print('返回主菜单。\n')
            break
        else:
            print('无效的命令，请重新输入。')

if __name__ == '__main__':
    # 可供选择的文件扩展名列表
    available_extensions = [
        '.py', '.java', '.cpp', '.c', '.h', '.cs', '.js', '.ts',
        '.jsx', '.tsx', '.rb', '.go', '.php', '.swift', '.kt',
        '.m', '.mm', '.txt', '.md', '.ini', '.cfg', '.json', '.xml',
        '.yaml', '.yml'
    ]

    # 初始化默认的源代码文件扩展名集合
    source_extensions = [
        '.py', '.java', '.cpp', '.c', '.h', '.cs', '.js', '.ts',
        '.jsx', '.tsx', '.rb', '.go', '.php', '.swift', '.kt',
        '.m', '.mm'
    ]

    # 设置日志文件路径
    script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
    log_file = os.path.join(script_directory, 'backup.log')
    setup_logging(log_file)

    while True:
        print('====================================')
        print('欢迎使用代码备份工具1.3.0')
        print('由Jack编写与制作:)')
        print('====================================')
        print('请输入操作命令：')
        print('[按回车或其他键开始备份] [set/s 设置文件后缀] [help/h 显示帮助] [exit/0 退出程序]')
        command = input('> ').strip().lower()

        if command in ('set', 's'):
            manage_extensions(source_extensions, available_extensions)
            continue
        elif command in ('help', 'h'):
            display_help()
            input('按回车键返回主菜单...')
            continue
        elif command in ('exit', '0'):
            print('\n程序已退出')
            break
        else:
            # 开始备份流程
            pass  # 继续执行下面的备份代码

        print('\n请按照提示进行操作：\n')

        project_directory = input('请输入项目路径（绝对路径）：\n> ').strip()
        if not project_directory:
            print('错误：未提供项目路径，请重新输入。\n')
            continue

        if not os.path.isdir(project_directory):
            print('错误：指定的路径不存在或不是有效的目录，请重新输入。\n')
            continue

        # 获取保存路径
        save_directory = input('请输入保存备份文件的路径（绝对路径，默认保存到脚本所在目录下的 backup_code 文件夹）：\n> ').strip()
        if not save_directory:
            # 默认保存到脚本路径下的 backup_code 文件夹
            save_directory = os.path.join(script_directory, 'backup_code')
        if not os.path.exists(save_directory):
            try:
                os.makedirs(save_directory)
            except Exception as e:
                print(f'错误：无法创建保存目录。{e}\n')
                logging.error(f'无法创建保存目录：{save_directory}，错误：{e}')
                continue

        # 创建项目的备份文件夹
        project_name = os.path.basename(os.path.abspath(project_directory))
        project_backup_folder = os.path.join(save_directory, project_name)

        # 检查是否存在同名的备份
        unique_suffix = 1
        base_backup_folder = project_backup_folder
        while os.path.exists(project_backup_folder):
            project_backup_folder = f"{base_backup_folder}_{unique_suffix}"
            unique_suffix += 1

        try:
            os.makedirs(project_backup_folder)
        except Exception as e:
            print(f'错误：无法创建项目备份文件夹。{e}\n')
            logging.error(f'无法创建项目备份文件夹：{project_backup_folder}，错误：{e}')
            continue

        # 获取当前时间，精确到分钟
        current_time = datetime.now().strftime('%Y%m%d_%H%M')
        # 输出文件名为项目目录名加时间戳
        output_filename = f'{project_name}_{current_time}.md'
        output_path = os.path.join(project_backup_folder, output_filename)

        # 询问是否压缩备份结果
        compress_choice = input('是否将备份结果压缩为zip文件？(y/n，默认n)：\n> ').strip().lower()
        if compress_choice not in ('y', 'yes'):
            compress_choice = False
        else:
            compress_choice = True

        logging.info('开始整理项目文件...')
        print('\n开始整理项目文件，请稍候...\n')
        write_code_and_structure(project_directory, output_path, tuple(source_extensions))

        if compress_choice:
            # 压缩备份结果
            zip_file_path = compress_backup(output_path)
        else:
            zip_file_path = None

        print('\n------------------------------------')
        print(f'整理完成，结果已保存到：\n{output_path}')
        if zip_file_path:
            print(f'备份文件已压缩为：\n{zip_file_path}')
        print('------------------------------------\n')

        logging.info(f'备份完成，结果已保存到：{output_path}')
        if zip_file_path:
            logging.info(f'备份文件已压缩为：{zip_file_path}')

        print('请输入操作编号：')
        print('1. 继续备份其他项目')
        print('0. 退出程序')
        choice = input('> ').strip()
        if choice == '1':
            print('\n即将开始新的备份操作...\n')
            continue
        elif choice == '0':
            print('\n程序已退出')
            break
        else:
            print('\n错误：无效的输入，程序将退出。')
            break