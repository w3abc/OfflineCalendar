#!/bin/bash

# 万年历本地版 - AppImage 安装脚本
# 适用于 Linux Mint, Ubuntu, Fedora 等主流 Linux 发行版

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
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

# 检查 AppImage 文件是否存在
check_appimage() {
    if [ ! -f "万年历本地版-x86_64.AppImage" ]; then
        print_error "找不到 '万年历本地版-x86_64.AppImage' 文件！"
        print_info "请确保安装脚本和 AppImage 文件在同一个目录中。"
        exit 1
    fi
    print_success "找到 AppImage 文件"
}

# 检查依赖
check_dependencies() {
    print_info "检查系统依赖..."

    # 检查是否为 x86_64 架构
    if [ "$(uname -m)" != "x86_64" ]; then
        print_error "此 AppImage 仅支持 x86_64 架构，当前架构：$(uname -m)"
        exit 1
    fi

    print_success "系统架构检查通过"
}

# 创建安装目录
create_directory() {
    INSTALL_DIR="$HOME/.local/bin"
    DESKTOP_DIR="$HOME/.local/share/applications"
    ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

    print_info "创建安装目录..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$DESKTOP_DIR"
    mkdir -p "$ICON_DIR"

    print_success "安装目录已创建：$INSTALL_DIR"
}

# 安装 AppImage
install_appimage() {
    APPIMAGE_NAME="万年历本地版.AppImage"
    DEST_PATH="$INSTALL_DIR/$APPIMAGE_NAME"

    print_info "安装 AppImage 到 $DEST_PATH..."

    # 复制 AppImage
    cp "万年历本地版-x86_64.AppImage" "$DEST_PATH"
    chmod +x "$DEST_PATH"

    print_success "AppImage 已安装到：$DEST_PATH"
}

# 提取并安装图标
extract_icon() {
    ICON_DEST="$ICON_DIR/wannianli.png"

    print_info "提取应用图标..."

    # 尝试从 AppImage 提取图标
    if ./"万年历本地版-x86_64.AppImage" --appimage-extract >/dev/null 2>&1; then
        if [ -f "squashfs-root/usr/share/icons/hicolor/256x256/apps/wannianli.png" ]; then
            cp "squashfs-root/usr/share/icons/hicolor/256x256/apps/wannianli.png" "$ICON_DEST"
            print_success "从 AppImage 提取图标成功"
        elif [ -f "squashfs-root/.DirIcon" ]; then
            cp "squashfs-root/.DirIcon" "$ICON_DEST"
            print_success "从 AppImage 提取 .DirIcon 成功"
        else
            # 如果提取失败，使用内置图标（假设存在）
            if [ -f "wannianli-icon.png" ]; then
                cp "wannianli-icon.png" "$ICON_DEST"
                print_success "使用内置图标文件"
            elif [ -f "icon.png" ]; then
                cp "icon.png" "$ICON_DEST"
                print_success "使用内置图标文件"
            else
                # 创建一个简单的图标（最后备选）
                print_warning "无法提取图标，将使用默认图标"
                return 0
            fi
        fi

        # 清理提取的临时文件
        rm -rf squashfs-root

        chmod 644 "$ICON_DEST"
        print_success "图标已安装到：$ICON_DEST"
    else
        # 如果 AppImage 不支持提取，尝试使用本地图标文件
        if [ -f "wannianli-icon.png" ]; then
            cp "wannianli-icon.png" "$ICON_DEST"
            chmod 644 "$ICON_DEST"
            print_success "使用本地图标文件：$ICON_DEST"
        elif [ -f "icon.png" ]; then
            cp "icon.png" "$ICON_DEST"
            chmod 644 "$ICON_DEST"
            print_success "使用本地图标文件：$ICON_DEST"
        else
            print_warning "未找到图标文件，将使用默认图标"
        fi
    fi
}

# 创建桌面文件
create_desktop_entry() {
    DESKTOP_FILE="$DESKTOP_DIR/wannianli.desktop"

    print_info "创建桌面集成..."

    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=万年历本地版
Name[zh_CN]=万年历本地版
Comment=Offline Chinese Calendar with Lunar Support
Comment[zh_CN]=离线中文万年历，支持农历显示
Exec=$INSTALL_DIR/万年历本地版.AppImage
Icon=wannianli
Terminal=false
Categories=Office;Calendar;
StartupNotify=true
Keywords=calendar;lunar;chinese;万年历;农历;节假日
EOF

    # 更新桌面数据库和图标缓存
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" 2>/dev/null || true

    print_success "桌面集成已创建"
}

# 添加到 PATH
add_to_path() {
    if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
        print_info "将 $INSTALL_DIR 添加到 PATH..."

        # 添加到 .bashrc
        echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$HOME/.bashrc"

        # 添加到 .zshrc (如果存在)
        if [ -f "$HOME/.zshrc" ]; then
            echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$HOME/.zshrc"
        fi

        print_warning "请重新打开终端或运行 'source ~/.bashrc' 以更新 PATH"
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    print_success "安装完成！"
    echo ""
    echo -e "${GREEN}使用方法：${NC}"
    echo "1. 在应用菜单中搜索 '万年历本地版'"
    echo "2. 或在终端运行：万年历本地版.AppImage"
    echo ""
    echo -e "${GREEN}文件位置：${NC}"
    echo "AppImage：$INSTALL_DIR/万年历本地版.AppImage"
    echo "桌面文件：$DESKTOP_DIR/wannianli.desktop"
    echo "图标文件：$ICON_DIR/wannianli.png"
    echo ""
    echo -e "${GREEN}卸载方法：${NC}"
    echo "1. 删除 AppImage：rm '$INSTALL_DIR/万年历本地版.AppImage'"
    echo "2. 删除桌面文件：rm '$DESKTOP_DIR/wannianli.desktop'"
    echo "3. 删除图标文件：rm '$ICON_DIR/wannianli.png'"
    echo ""
}

# 主函数
main() {
    echo -e "${BLUE}"
    echo "================================"
    echo "   万年历本地版 - AppImage 安装"
    echo "================================"
    echo -e "${NC}"

    check_appimage
    check_dependencies
    create_directory
    install_appimage
    extract_icon
    create_desktop_entry
    add_to_path
    show_completion
}

# 运行主函数
main "$@"