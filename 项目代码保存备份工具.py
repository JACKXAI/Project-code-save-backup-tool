import os
import sys
from datetime import datetime

def get_code_files(directory):
    """
    遍历指定路径下的所有文件和子目录，收集源代码文件的路径。
    """
    code_files = []
    # 定义源代码文件的扩展名集合
    source_extensions = (
        '.py', '.java', '.cpp', '.c', '.h', '.cs', '.js', '.ts',
        '.jsx', '.tsx', '.rb', '.go', '.php', '.swift', '.kt',
        '.m', '.mm'
    )
    for root, _, files in os.walk(directory):
        for file in files:
            # 判断文件是否为源代码文件
            if file.endswith(source_extensions):
                file_path = os.path.join(root, file)
                code_files.append(file_path)
    return code_files

def get_directory_tree(directory):
    """
    获取目录的树状结构字符串，显示每个文件夹和文件的名称，从上到下展开，类似于 VSCode 的文件树。
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
    根据文件扩展名，返回对应的语言类型，供 Markdown 代码块使用。
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
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.rb': 'ruby',
        '.go': 'go',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.m': 'objective-c',
        '.mm': 'objective-c',
    }
    return language_map.get(extension, '')

def write_code_and_structure(directory, output_file):
    """
    将项目的目录结构和所有源代码文件的内容以 Markdown 格式写入指定的输出文件。
    """
    code_files = get_code_files(directory)
    total_files = len(code_files)
    processed_files = 0

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
            for file_path in code_files:
                processed_files += 1
                relative_path = os.path.relpath(file_path, directory)
                out_file.write(f'### 文件：{relative_path}\n\n')
                out_file.write('```{0}\n'.format(get_language_from_extension(file_path)))
                try:
                    with open(file_path, 'r', encoding='utf-8') as code_file:
                        out_file.write(code_file.read())
                except UnicodeDecodeError:
                    # 如果编码错误，尝试使用其他编码读取
                    try:
                        with open(file_path, 'r', encoding='latin-1') as code_file:
                            out_file.write(code_file.read())
                    except Exception as e:
                        out_file.write(f'无法读取文件 {relative_path}，错误信息：{e}\n')
                out_file.write('```\n\n')
                if total_files > 10 and processed_files % (total_files // 10) == 0:
                    print(f'进度：已处理 {processed_files}/{total_files} 个文件...')
    except Exception as e:
        print(f'写入输出文件时发生错误：{e}')
        sys.exit(1)

if __name__ == '__main__':
    while True:
        print('====================================')
        print('代码备份工具_0.0.5')
        print('请按照提示进行操作：')
        print('')

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
            script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
            save_directory = os.path.join(script_directory, 'backup_code')
        if not os.path.exists(save_directory):
            try:
                os.makedirs(save_directory)
            except Exception as e:
                print(f'错误：无法创建保存目录。{e}\n')
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
            continue

        # 获取当前时间，精确到分钟
        current_time = datetime.now().strftime('%Y%m%d_%H%M')
        # 输出文件名为项目目录名加时间戳
        output_filename = f'{project_name}_{current_time}.md'
        output_path = os.path.join(project_backup_folder, output_filename)

        print('\n开始整理项目文件，请稍候...\n')
        write_code_and_structure(project_directory, output_path)

        print('\n------------------------------------')
        print(f'整理完成，结果已保存到：\n{output_path}')
        print('------------------------------------\n')

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