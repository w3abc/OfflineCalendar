#!/bin/bash

# 万年历本地版 - 自动构建脚本
# 用于重新构建 AppImage 分发包

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${PURPLE}"
    echo "=================================================="
    echo "         万年历本地版 - 自动构建脚本"
    echo "=================================================="
    echo -e "${NC}"
}

print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

print_step() {
    echo -e "${CYAN}[步骤]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_step "检查构建依赖..."

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        print_error "未找到 python3，请先安装 Python 3"
        exit 1
    fi

    # 检查是否存在虚拟环境
    if [ ! -d "venv" ]; then
        print_warning "未找到虚拟环境，将重新创建..."
        create_venv
    fi

    print_success "依赖检查完成"
}

# 创建虚拟环境
create_venv() {
    print_step "创建 Python 虚拟环境..."

    python3 -m venv venv
    source venv/bin/activate

    # 升级 pip
    pip install --upgrade pip

    # 安装依赖
    pip install -r requirements.txt
    pip install pyinstaller

    print_success "虚拟环境创建完成"
}

# 激活虚拟环境
activate_venv() {
    print_step "激活虚拟环境..."
    source venv/bin/activate
    print_success "虚拟环境已激活"
}

# 清理旧的构建文件
clean_build() {
    print_step "清理旧的构建文件..."

    # 清理 PyInstaller 文件
    rm -rf build/ dist/ *.spec

    # 清理 AppImage 文件
    rm -rf appimage/squashfs-root/
    rm -f appimage/*.AppImage
    rm -rf appimage/WanNianLi.AppDir/

    # 清理临时文件
    rm -f wannianli-icon.png

    print_success "构建文件清理完成"
}

# 使用 PyInstaller 构建
build_pyinstaller() {
    print_step "使用 PyInstaller 构建可执行文件..."

    # 确保图标文件存在
    if [ ! -f "icon.png" ]; then
        print_error "找不到 icon.png 文件！"
        exit 1
    fi

    # 使用 PyInstaller 构建
    pyinstaller --name="万年历本地版" --onefile --windowed --icon=icon.png --add-data="icon.png:." main.py

    print_success "PyInstaller 构建完成"
}

# 创建 AppImage
create_appimage() {
    print_step "创建 AppImage..."

    # 创建 AppDir 目录结构
    rm -rf appimage/WanNianLi.AppDir
    mkdir -p appimage/WanNianLi.AppDir/usr/bin
    mkdir -p appimage/WanNianLi.AppDir/usr/share/icons/hicolor/256x256/apps

    # 复制可执行文件
    cp dist/万年历本地版 appimage/WanNianLi.AppDir/usr/bin/

    # 复制图标文件
    cp icon.png appimage/WanNianLi.AppDir/usr/share/icons/hicolor/256x256/apps/wannianli.png
    cp icon.png appimage/WanNianLi.AppDir/wannianli.png

    # 创建 desktop 文件
    cat > appimage/WanNianLi.AppDir/wannianli.desktop << EOF
[Desktop Entry]
Type=Application
Name=万年历本地版
Name[zh_CN]=万年历本地版
Comment=Offline Chinese Calendar with Lunar Support
Comment[zh_CN]=离线中文万年历，支持农历显示
Exec=万年历本地版
Icon=wannianli
Terminal=false
Categories=Office;Calendar;
StartupNotify=true
Keywords=calendar;lunar;chinese;万年历;农历;节假日
EOF

    # 创建 AppRun 脚本
    cat > appimage/WanNianLi.AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin/:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib/:${LD_LIBRARY_PATH}"
export XDG_DATA_DIRS="${HERE}/usr/share/:${XDG_DATA_DIRS}"
exec "${HERE}/usr/bin/万年历本地版" "$@"
EOF

    # 设置权限
    chmod +x appimage/WanNianLi.AppDir/AppRun

    # 下载 AppImageTool（如果不存在）
    if [ ! -f "appimage/appimagetool-x86_64.AppImage" ]; then
        print_info "下载 AppImageTool..."
        mkdir -p appimage
        cd appimage
        wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
        chmod +x appimagetool-x86_64.AppImage
        cd ..
    fi

    # 创建 AppImage
    print_info "生成 AppImage 文件..."
    cd appimage
    ARCH=x86_64 ./appimagetool-x86_64.AppImage WanNianLi.AppDir
    cd ..

    print_success "AppImage 创建完成"
}

# 创建分发包
create_distribution() {
    print_step "创建分发包..."

    # 复制 AppImage 到根目录
    cp appimage/万年历本地版-x86_64.AppImage ./

    # 创建图标文件副本
    cp icon.png wannianli-icon.png

    # 获取版本信息（基于时间戳）
    VERSION=$(date +"%Y%m%d_%H%M%S")

    print_success "分发包创建完成"
}

# 显示构建结果
show_build_result() {
    echo ""
    print_success "构建完成！"
    echo ""
    echo -e "${GREEN}构建文件：${NC}"
    for file in 万年历本地版-x86_64.AppImage install.sh wannianli-icon.png README_用户安装指南.md; do
        if [ -f "$file" ]; then
            echo "$(ls -lh "$file" | awk '{print $5, $9}')"
        fi
    done
    echo ""
    echo -e "${GREEN}测试命令：${NC}"
    echo "1. 测试 AppImage: ./万年历本地版-x86_64.AppImage"
    echo "2. 测试安装: ./install.sh"
    echo ""
    echo -e "${GREEN}分发文件：${NC}"
    echo "可以将以下文件打包分发："
    echo "- 万年历本地版-x86_64.AppImage"
    echo "- install.sh"
    echo "- wannianli-icon.png"
    echo "- README_用户安装指南.md"
    echo ""
}

# 清理函数
cleanup_on_exit() {
    if [ $? -ne 0 ]; then
        print_error "构建过程中出现错误"
    fi
}

# 主函数
main() {
    # 设置错误处理
    trap cleanup_on_exit EXIT

    print_header

    # 解析命令行参数
    CLEAN_ONLY=false
    SKIP_CLEAN=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean-only)
                CLEAN_ONLY=true
                shift
                ;;
            --skip-clean)
                SKIP_CLEAN=true
                shift
                ;;
            -h|--help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --clean-only    仅清理构建文件，不执行构建"
                echo "  --skip-clean    跳过清理步骤"
                echo "  -h, --help      显示此帮助信息"
                echo ""
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                echo "使用 -h 或 --help 查看帮助"
                exit 1
                ;;
        esac
    done

    # 如果只是清理，执行清理后退出
    if [ "$CLEAN_ONLY" = true ]; then
        clean_build
        print_success "清理完成"
        exit 0
    fi

    # 检查依赖
    check_dependencies

    # 激活虚拟环境
    activate_venv

    # 清理旧文件（除非跳过）
    if [ "$SKIP_CLEAN" = false ]; then
        clean_build
    fi

    # 构建步骤
    build_pyinstaller
    create_appimage
    create_distribution

    # 显示结果
    show_build_result
}

# 运行主函数
main "$@"