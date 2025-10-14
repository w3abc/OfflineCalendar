#!/bin/bash

# 万年历本地版 - 快速重建脚本
# 用于程序修改后快速重新构建

set -e

echo "🚀 万年历本地版 - 快速重建"
echo "=============================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 未找到虚拟环境，请先运行 ./build.sh 进行完整构建"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 清理旧的构建文件
echo "🧹 清理旧文件..."
rm -rf build/ dist/ *.spec
rm -rf appimage/squashfs-root/
rm -f appimage/*.AppImage
rm -rf appimage/WanNianLi.AppDir/
rm -f 万年历本地版-x86_64.AppImage wannianli-icon.png

# 使用 PyInstaller 构建
echo "📦 构建可执行文件..."
pyinstaller --name="万年历本地版" --onefile --windowed --icon=icon.png --add-data="icon.png:." main.py

# 创建 AppImage
echo "🎯 创建 AppImage..."

# AppDir 结构
rm -rf appimage/WanNianLi.AppDir
mkdir -p appimage/WanNianLi.AppDir/usr/bin
mkdir -p appimage/WanNianLi.AppDir/usr/share/icons/hicolor/256x256/apps

cp dist/万年历本地版 appimage/WanNianLi.AppDir/usr/bin/
cp icon.png appimage/WanNianLi.AppDir/usr/share/icons/hicolor/256x256/apps/wannianli.png
cp icon.png appimage/WanNianLi.AppDir/wannianli.png

# Desktop 文件
cat > appimage/WanNianLi.AppDir/wannianli.desktop << 'EOF'
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

# AppRun 脚本
cat > appimage/WanNianLi.AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin/:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib/:${LD_LIBRARY_PATH}"
export XDG_DATA_DIRS="${HERE}/usr/share/:${XDG_DATA_DIRS}"
exec "${HERE}/usr/bin/万年历本地版" "$@"
EOF

chmod +x appimage/WanNianLi.AppDir/AppRun

# 生成 AppImage
cd appimage
ARCH=x86_64 ./appimagetool-x86_64.AppImage WanNianLi.AppDir
cd ..

# 复制到根目录
cp appimage/万年历本地版-x86_64.AppImage ./
cp icon.png wannianli-icon.png

echo ""
echo "✅ 构建完成！"
echo ""
echo "📁 分发文件："
ls -lh 万年历本地版-x86_64.AppImage install.sh wannianli-icon.png README_用户安装指南.md
echo ""
echo "🧪 测试命令："
echo "   ./万年历本地版-x86_64.AppImage"
echo ""