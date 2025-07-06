#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path


def check_requirements():
    print("检查打包环境...")

    if sys.version_info < (3, 7):
        print("错误: 需要 Python 3.7 或更高版本")
        return False

    required_packages = ['pyinstaller', 'requests', 'playwright']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"缺少必要的包: {', '.join(missing_packages)}")
        print("正在使用清华源安装...")
        subprocess.check_call([
                                  sys.executable, '-m', 'pip', 'install',
                                  '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'
                              ] + missing_packages)

    return True


def prepare_playwright():
    print("\n准备 Playwright 浏览器...")

    import playwright
    playwright_path = Path(playwright.__file__).parent

    print("下载 Chromium 浏览器...")
    subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])

    if platform.system() == 'Windows':
        chromium_path = Path.home() / 'AppData' / 'Local' / 'ms-playwright'
    elif platform.system() == 'Darwin':
        chromium_path = Path.home() / 'Library' / 'Caches' / 'ms-playwright'
    else:
        chromium_path = Path.home() / '.cache' / 'ms-playwright'

    return str(playwright_path), str(chromium_path)


def create_spec_file():
    print("\n创建打包配置文件...")

    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

import playwright
playwright_path = Path(playwright.__file__).parent

if sys.platform == 'win32':
    browser_path = Path.home() / 'AppData' / 'Local' / 'ms-playwright'
elif sys.platform == 'darwin':
    browser_path = Path.home() / 'Library' / 'Caches' / 'ms-playwright'
else:
    browser_path = Path.home() / '.cache' / 'ms-playwright'

a = Analysis(
    ['downloader.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(playwright_path), 'playwright'),
        (str(browser_path), 'ms-playwright'),
    ],
    hiddenimports=[
        'playwright',
        'playwright.sync_api',
        'playwright._impl',
        'playwright._impl._sync_base',
        'playwright._impl._browser',
        'playwright._impl._browser_context',
        'playwright._impl._page',
        'playwright._impl._element_handle',
        'playwright._impl._network',
        'playwright._impl._transport',
        'playwright._impl._connection',
        'playwright._impl._api_types',
        'playwright._impl._api_structures',
        'playwright._impl._helper',
        'playwright._impl._errors',
        'playwright._impl._glob',
        'playwright._impl._impl_to_api_mapping',
        'playwright._impl._path_utils',
        'playwright._impl._str_utils',
        'playwright._impl._greenlets',
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PDF下载器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''

    with open('pdf_downloader.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)


def create_runtime_hook():
    print("创建运行时钩子...")

    hook_content = '''# -*- coding: utf-8 -*-
import os
import sys

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(base_path, 'ms-playwright')
    os.environ['PLAYWRIGHT_DRIVER_PATH'] = os.path.join(base_path, 'playwright', 'driver', 'package', 'cli.js')

    playwright_path = os.path.join(base_path, 'playwright')
    if playwright_path not in sys.path:
        sys.path.insert(0, playwright_path)
'''

    with open('runtime_hook.py', 'w', encoding='utf-8') as f:
        f.write(hook_content)


def build_exe():
    print("\n开始打包...")

    cmd = [sys.executable, '-m', 'PyInstaller', 'pdf_downloader.spec', '--clean']

    try:
        subprocess.check_call(cmd)
        print("\n✅ 打包成功!")

        exe_path = Path('dist') / 'PDF下载器.exe'
        if exe_path.exists():
            print(f"生成的文件: {exe_path.absolute()}")
            print(f"文件大小: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        return False

    return True


def create_readme():
    print("\n创建使用说明...")

    readme_content = '''PDF下载器 v5.0

使用方法：
1. 双击 PDF下载器.exe 启动程序
2. 在地址栏输入网址或 PDF 链接
3. 点击"开始下载"

功能：
- 下载PDF文件
- 网页转PDF
- 自动处理弹窗
- 智能滚动加载

系统要求：
- Windows 7/8/10/11 (64位)
- 至少 4GB 内存

开源地址：
https://github.com/yourusername/pdf-downloader
'''

    with open('README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)


def main():
    print("PDF下载器打包工具")
    print("=" * 50)

    if not os.path.exists('downloader.py'):
        print("错误: 找不到 downloader.py")
        return

    if not check_requirements():
        return

    try:
        playwright_path, browser_path = prepare_playwright()
    except Exception as e:
        print(f"准备 Playwright 失败: {e}")
        return

    create_spec_file()
    create_runtime_hook()
    create_readme()

    if build_exe():
        print("\n" + "=" * 50)
        print("✅ 打包完成!")
        print("\n生成的文件:")
        print("  - dist/PDF下载器.exe (主程序)")
        print("  - README.txt (使用说明)")

    for file in ['pdf_downloader.spec', 'runtime_hook.py']:
        if os.path.exists(file):
            os.remove(file)

    print("\n完成! 按任意键退出...")
    input()


if __name__ == '__main__':
    main()