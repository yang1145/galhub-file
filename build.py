#!/usr/bin/env python3
"""
GalHub 文件管理系统构建脚本
用于打包和编译项目为exe可执行文件
"""

import os
import sys
import shutil
import subprocess
import zipfile
from datetime import datetime

def check_pyinstaller():
    """检查PyInstaller是否已安装"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """安装PyInstaller"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyInstaller"])
        print("PyInstaller 安装成功")
        return True
    except subprocess.CalledProcessError:
        print("PyInstaller 安装失败")
        return False

def create_spec_file():
    """创建PyInstaller spec文件用于构建带控制台的exe"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('config.py', '.'), ('files.db', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='galhub-file',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保持控制台窗口开启
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('galhub-file.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("创建 spec 文件: galhub-file.spec")

def build_executable():
    """构建带控制台的exe可执行文件"""
    print("正在构建带控制台的exe可执行文件...")
    
    # 创建spec文件
    create_spec_file()
    
    # 运行PyInstaller
    try:
        result = subprocess.run([
            sys.executable, '-m', 'PyInstaller', 
            '--noconfirm', 'galhub-file.spec'
        ], check=True, capture_output=True, text=True)
        
        print("可执行文件构建成功!")
        print("可执行文件位置: dist/galhub-file.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print("错误: 未找到 PyInstaller。请确保已安装 PyInstaller。")
        return False

def create_dist_folder():
    """创建分发目录"""
    if not os.path.exists('dist'):
        os.makedirs('dist')
        print("创建 dist 目录")

def copy_additional_files():
    """复制额外需要的文件到dist目录"""
    print("正在复制额外文件...")
    
    # 复制requirements.txt
    if os.path.exists('requirements.txt'):
        shutil.copy2('requirements.txt', 'dist/')
        print("复制 requirements.txt")
    
    # 复制README.md
    if os.path.exists('README.md'):
        shutil.copy2('README.md', 'dist/')
        print("复制 README.md")
    
    # 复制LICENSE
    if os.path.exists('LICENSE'):
        shutil.copy2('LICENSE', 'dist/')
        print("复制 LICENSE")

def create_portable_package():
    """创建便携式包（包含exe和必要文件）"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    package_name = f'galhub-file-portable_{timestamp}.zip'
    package_path = os.path.join('dist', package_name)
    
    print(f"正在创建便携式包: {package_name}")
    
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('dist'):
            # 跳过zip文件本身
            if root == 'dist' and package_name in files:
                continue
                
            for file in files:
                if file != package_name and file.endswith(('.exe', '.txt', '.md')):
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, 'dist')
                    zipf.write(file_path, arc_path)
    
    print(f"便携式包创建完成: {package_name}")
    return package_path

def main():
    """主函数"""
    print("GalHub 文件管理系统 EXE 构建工具")
    print("=" * 50)
    
    # 检查是否在项目根目录
    if not os.path.exists('app.py') or not os.path.exists('templates'):
        print("错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 检查PyInstaller
    if not check_pyinstaller():
        print("未检测到 PyInstaller")
        choice = input("是否自动安装 PyInstaller? (y/n): ")
        if choice.lower() == 'y':
            if not install_pyinstaller():
                print("安装失败，无法继续构建")
                sys.exit(1)
        else:
            print("需要安装 PyInstaller 才能构建exe文件")
            sys.exit(1)
    
    # 创建分发目录
    create_dist_folder()
    
    # 构建可执行文件
    if build_executable():
        # 复制额外文件
        copy_additional_files()
        
        # 创建便携式包
        package_path = create_portable_package()
        
        print("\n构建完成!")
        print(f"可执行文件位置: dist/galhub-file.exe")
        print(f"便携式包位置: {package_path}")
    else:
        print("\n构建失败!")
        sys.exit(1)

if __name__ == '__main__':
    main()