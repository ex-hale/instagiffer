VENV := .venv

ifeq ($(OS),Windows_NT)
	PLATFORM := windows
	SHELL		:= C:/Program Files/Git/usr/bin/sh.exe
	export PATH	:= C:/Program Files/Git/usr/bin:$(PATH)
	PYTHON		:= $(VENV)/Scripts/python
	PYTHON_CMD	:= py -3.13
	VENV_STAMP	:= $(VENV)/Scripts/activate
else
	PLATFORM := $(shell uname -s | tr '[:upper:]' '[:lower:]')
	PYTHON		:= $(VENV)/bin/python3
	PYTHON_CMD	:= python3
	VENV_STAMP	:= $(VENV)/bin/activate
endif

PIP			:= $(PYTHON) -m pip
VERSION		:= $(shell grep -m1 '__version__' instagiffer.py | awk -F'"' '{print $$2}')
DEPS_STAMP	:= build/.deps-stamp
DIST_STAMP	:= build/.dist-stamp

TEST_VIDEO_URLS := \
	https://www.youtube.com/watch?v=aqz-KE-bpKQ \
	https://www.youtube.com/watch?v=L_uXZEkhlZU

.PHONY: init run test test-app test-videos lint format clean help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "General:"
	@echo "  init         Set up the virtual Python environment."
	@echo "  run          Run local Instagiffer app."
	@echo "  lint         Run the linter."
	@echo "  format       Run the formatter."
	@echo "  test         Run formatter, linter and tests."
	@echo "  clean        Clean build artifacts."
	@echo ""
	@echo "Platform (current: $(PLATFORM)):"
	@echo "  deps         Download platform dependencies."
	@echo "  dist         Build a distributable package."
	@echo "  install      Install the application."
	@echo "  redeps       Re-download dependencies."
	@echo "  redist       Force full rebuild."

init: $(VENV_STAMP)

$(VENV_STAMP): pyproject.toml
	$(PYTHON_CMD) -m venv $(VENV)
	$(PIP) install -e ".[dev]"
	@echo "Done. Activate with: source $(VENV_STAMP)"

run: init
	$(PYTHON) main.py $(ARGS)

debug: init
	$(PYTHON) main.py --debug

lint: init
	$(PYTHON) -m pylint instagiffer.py main.py test/test_instagiffer.py test/instagiffer_automation.py test/conftest.py

format: init
	$(PYTHON) -m black instagiffer.py main.py test/test_instagiffer.py test/instagiffer_automation.py test/conftest.py

test-videos:
	@mkdir -p test/test_data
	@i=1; for url in $(TEST_VIDEO_URLS); do \
		if [ ! -f "test/test_data/test_video_$$i.mp4" ]; then \
			$(YTDLP) -f "worst[ext=mp4]/worst" -o "test/test_data/test_video_$$i.mp4" "$$url"; \
		fi; \
		i=$$((i + 1)); \
	done

test: init format lint test-videos
	$(PYTHON) -m pytest

test-app: install test-videos
	$(PYTHON) -m pytest "--app=$(INSTALL_PATH)"

clean:
	rm -rf $(VENV) __pycache__ test/__pycache__ .pytest_cache *.egg-info instagiffer-event.log
	rm -rf dist/ build/ deps/ *.pyc
	rm -rf test/test_data/

redeps:
	@rm -f $(DEPS_STAMP)
	$(MAKE) deps

redist:
	@rm -f $(DIST_STAMP)
	$(MAKE) dist


ifeq ($(PLATFORM),darwin)

APP_PATH		:= dist/Instagiffer.app
INSTALL_PATH	:= /Applications/Instagiffer.app
MAGICK_OUT		:= build/imagemagick/out
FFMPEG_URL		:= https://evermeet.cx/ffmpeg/getrelease/zip
YTDLP_URL		:= https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos
YTDLP			:= deps/mac/yt-dlp

deps: $(DEPS_STAMP)
$(DEPS_STAMP): $(VENV_STAMP)
	@command -v brew >/dev/null || (echo "Error: Homebrew is required. See https://brew.sh" && exit 1)
	@for pkg in python3 python-tk pkg-config cmake gperf gifsicle create-dmg; do \
		brew list $$pkg >/dev/null 2>&1 || brew install $$pkg; \
	done
	$(PIP) install -e ".[build-mac]"
	$(MAKE) -f imagemagick.mk
	@mkdir -p deps/mac
	@cp -R $(MAGICK_OUT)/* deps/mac/
	@echo "Downloading ffmpeg from $(FFMPEG_URL) ..."
	@[ -f deps/mac/ffmpeg ]   || (curl -fSL -o deps/mac/ffmpeg.zip "$(FFMPEG_URL)" && unzip -o deps/mac/ffmpeg.zip -d deps/mac/ && rm deps/mac/ffmpeg.zip && chmod +x deps/mac/ffmpeg)
	@echo "Downloading yt-dlp from $(YTDLP_URL) ..."
	@[ -f deps/mac/yt-dlp ]   || (curl -fSL -o deps/mac/yt-dlp "$(YTDLP_URL)" && chmod +x deps/mac/yt-dlp)
	@[ -f deps/mac/gifsicle ] || cp "$$(which gifsicle)" deps/mac/gifsicle
	@touch $@
	@echo "macOS dependencies ready in deps/mac/"

$(DIST_STAMP): $(VENV_STAMP) instagiffer.py main.py instagiffer.conf $(DEPS_STAMP)
	@echo "Building Mac release with PyInstaller ..."
	$(PYTHON) -m PyInstaller --log-level WARN release/Instagiffer-mac.spec --distpath dist --workpath build/pyinstaller --noconfirm
	codesign --force --deep --sign - $(APP_PATH)
	@touch $@

dist: $(DIST_STAMP)
	@rm -f dist/Instagiffer-$(VERSION).dmg
	create-dmg \
		--volname "Instagiffer" \
		--volicon "instagiffer.icns" \
		--background "assets/dmg_background.png" \
		--window-pos 200 120 \
		--window-size 640 480 \
		--icon-size 140 \
		--icon "Instagiffer.app" 120 160 \
		--app-drop-link 520 160 \
		--no-internet-enable \
		--hdiutil-quiet \
		"dist/Instagiffer-$(VERSION).dmg" \
		"$(APP_PATH)"
	@SIZE=$$(stat -f%z "dist/Instagiffer-$(VERSION).dmg"); echo "Built dist/Instagiffer-$(VERSION).dmg ($$(( SIZE / 1048576 ))MB)"

install: $(DIST_STAMP)
	@rm -rf $(INSTALL_PATH)
	cp -R $(APP_PATH) $(INSTALL_PATH)
	@echo "Installed to $(INSTALL_PATH)"


else ifeq ($(PLATFORM),windows)

APP_PATH		:= dist/Instagiffer
INSTALL_PATH	:= C:/Program Files/Instagiffer/Instagiffer.exe
ISCC			:= ISCC.exe
SEVENZIP		:= C:/Program Files/7-Zip/7z.exe
MAGICK_BINS		:= https://imagemagick.org/archive/binaries/
MAGICK_TYPE		:= -portable-Q8-x64.7z
MAGICK_VER		:= $(shell curl -fsSL $(MAGICK_BINS) | grep -oP 'ImageMagick-\K[\d.]+-\d+(?=$(MAGICK_TYPE))' | sort -V | tail -1)
MAGICK_URL		:= $(MAGICK_BINS)ImageMagick-$(MAGICK_VER)$(MAGICK_TYPE)
FFMPEG_URL		:= https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
YTDLP_URL		:= https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
YTDLP			:= deps/win/yt-dlp.exe
GIFSICLE_URL	:= https://eternallybored.org/misc/gifsicle/releases/gifsicle-1.95-win64.zip
INSTALL_STAMP	:= build/.install-stamp

deps: $(DEPS_STAMP)
$(DEPS_STAMP): $(VENV_STAMP)
	$(PIP) install -e ".[build-win,test-win]"
	@mkdir -p deps/win build
	@echo "Downloading ImageMagick from $(MAGICK_URL) ..."
	@[ -f deps/win/magick.exe ] || ( \
		curl -fSL -o build/magick-win.7z "$(MAGICK_URL)" && \
		"$(SEVENZIP)" e build/magick-win.7z -odeps/win -y "magick.exe" && \
		rm build/magick-win.7z )
	@echo "Downloading ffmpeg from $(FFMPEG_URL) ..."
	@[ -f deps/win/ffmpeg.exe ] || ( \
		curl -fSL -o build/ffmpeg-win.zip "$(FFMPEG_URL)" && \
		mkdir -p build/ffmpeg-tmp && \
		unzip -o build/ffmpeg-win.zip -d build/ffmpeg-tmp && \
		find build/ffmpeg-tmp -name ffmpeg.exe -exec cp {} deps/win/ \; && \
		rm -rf build/ffmpeg-win.zip build/ffmpeg-tmp )
	@echo "Downloading yt-dlp from $(YTDLP_URL) ..."
	@[ -f deps/win/yt-dlp.exe ] || curl -fSL -o deps/win/yt-dlp.exe "$(YTDLP_URL)"
	@echo "Downloading gifsicle from $(GIFSICLE_URL) ..."
	@[ -f deps/win/gifsicle.exe ] || ( \
		curl -fSL -o build/gifsicle-win.zip "$(GIFSICLE_URL)" && \
		unzip -jo build/gifsicle-win.zip "*.exe" -d deps/win/ && \
		rm build/gifsicle-win.zip )
	@touch $@
	@echo "Windows dependencies ready in deps/win/"

$(DIST_STAMP): $(VENV_STAMP) instagiffer.py main.py instagiffer.conf $(DEPS_STAMP)
	@echo "Building Windows release with PyInstaller ..."
	$(PYTHON) -m PyInstaller --log-level WARN release/Instagiffer-win.spec --distpath dist --workpath build/pyinstaller --noconfirm
	@touch $@

dist: $(DIST_STAMP)
	@rm -f dist/instagiffer-$(VERSION)-setup.exe
	@echo "Building Installer with Inno Setup ..."
	@MSYS_NO_PATHCONV=1 "$(ISCC)" /Q release/installer.iss /dMyAppVersion=$(VERSION)
	@SIZE=$$(stat -c%s "dist/instagiffer-$(VERSION)-setup.exe"); echo "Built dist/instagiffer-$(VERSION)-setup.exe ($$(( SIZE / 1048576 ))MB)"

install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(DIST_STAMP) release/installer.iss
	@rm -f dist/instagiffer-$(VERSION)-setup.exe
	@echo "Building Installer with Inno Setup ..."
	@MSYS_NO_PATHCONV=1 "$(ISCC)" /Q release/installer.iss /dMyAppVersion=$(VERSION)
	@echo "Calling Installer ..."
	@MSYS_NO_PATHCONV=1 dist/instagiffer-$(VERSION)-setup.exe /VERYSILENT /SUPPRESSMSGBOXES
	@touch $@
	@echo "Installed to $(INSTALL_PATH)"


else ifeq ($(PLATFORM),linux)

DEPS_DIR		:= deps/linux
APP_PATH		:= dist/Instagiffer/
MAGICK_URL		:= https://imagemagick.org/archive/binaries/magick
FFMPEG_URL		:= https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
FFMPEG_TMP		:= $(DEPS_DIR)/ffmpeg.tar.xz
YTDLP_URL		:= https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux

INSTALL_PATH	:= /opt/instagiffer
DEB_ROOT		:= dist/deb_pkg
DEB_OUT			:= dist/instagiffer_$(VERSION)_amd64.deb
DEB_COMPRESS	?= gzip # override with: make dist DEB_COMPRESS=xz

deps: $(DEPS_STAMP)
$(DEPS_STAMP): $(VENV_STAMP)
	$(PIP) install -e ".[build-linux]"
	@mkdir -p $(DEPS_DIR) build
	@[ -f $(DEPS_DIR)/magick ] || ( \
		echo "Downloading ImageMagick from $(MAGICK_URL) ..." && \
		curl -fSL -o $(DEPS_DIR)/magick "$(MAGICK_URL)" && \
		chmod +x $(DEPS_DIR)/magick )
	@[ -f $(DEPS_DIR)/ffmpeg ] || ( \
		echo "Downloading ffmpeg from $(FFMPEG_URL) ..." && \
		curl -fSL -o $(FFMPEG_TMP) "$(FFMPEG_URL)" && \
		tar -xf $(FFMPEG_TMP) -C $(DEPS_DIR)/ --strip-components=2 --wildcards "*/bin/ffmpeg" && \
		rm $(FFMPEG_TMP) && \
		chmod +x $(DEPS_DIR)/ffmpeg )
	@[ -f $(DEPS_DIR)/yt-dlp ] || ( \
		echo "Downloading yt-dlp from $(YTDLP_URL) ..." && \
		curl -fSL -o $(DEPS_DIR)/yt-dlp "$(YTDLP_URL)" && \
		chmod +x $(DEPS_DIR)/yt-dlp )
# 	lets ignore gifsicle for now
# 	@[ -f $(DEPS_DIR)/gifsicle ] || cp "$$(which gifsicle)" $(DEPS_DIR)/gifsicle
	@touch $@
	@echo "Linux dependencies ready in $(DEPS_DIR)"

$(DIST_STAMP): $(VENV_STAMP) instagiffer.py main.py instagiffer.conf $(DEPS_STAMP)
	@echo "Building Linux release with PyInstaller ..."
	$(PYTHON) -m PyInstaller --log-level WARN release/Instagiffer-linux.spec --distpath dist --workpath build/pyinstaller --noconfirm
	@touch $@

dist: $(DIST_STAMP)
	@echo "  Building package tree ..."
	@rm -rf $(DEB_ROOT)
	@mkdir -p $(DEB_ROOT)/DEBIAN
	@mkdir -p $(DEB_ROOT)$(INSTALL_PATH)
	@mkdir -p $(DEB_ROOT)/usr/share/applications
	@mkdir -p $(DEB_ROOT)/usr/share/icons/hicolor/256x256/apps
	@mkdir -p dist

	@echo "  Copying app files ..."
	@cp -r $(APP_PATH)/. $(DEB_ROOT)$(INSTALL_PATH)/
	@echo "  Writing control file ..."
	@printf '%s\n' \
		'Package: instagiffer' \
		'Version: $(VERSION)' \
		'Architecture: amd64' \
		'Installed-Size: '"$$(du -sk $(DEB_ROOT)$(INSTALL_PATH) | cut -f1)" \
		'Maintainer: Justin Todd <instagiffer@gmail.com>' \
		'Depends: ffmpeg, imagemagick' \
		'Description: The easy way to make GIFs from videos' \
		'Homepage: https://github.com/ex-hale/instagiffer' \
		> $(DEB_ROOT)/DEBIAN/control

	@echo "  Writing postinst ..."
	@printf '%s\n' \
		'#!/bin/bash' \
		'ln -sf $(INSTALL_PATH)/Instagiffer /usr/local/bin/instagiffer' \
		'update-desktop-database /usr/share/applications/ 2>/dev/null || true' \
		'gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true' \
		> $(DEB_ROOT)/DEBIAN/postinst
	@chmod 755 $(DEB_ROOT)/DEBIAN/postinst

	@echo "  Copying desktop file and icon ..."
	@printf '%s\n' \
		'[Desktop Entry]' \
		'Name=Instagiffer' \
		'Comment=The easy way to make GIFs from videos' \
		'Exec=$(INSTALL_PATH)/Instagiffer' \
		'Icon=instagiffer' \
		'Type=Application' \
		'Categories=Graphics;Video;' \
		'Terminal=false' \
		> $(DEB_ROOT)/usr/share/applications/instagiffer.desktop
	@cp assets/logo.png $(DEB_ROOT)/usr/share/icons/hicolor/256x256/apps/instagiffer.png

	@echo "  Building .deb (compressing with $(DEB_COMPRESS))..."
	@dpkg-deb -Z$(DEB_COMPRESS) --build $(DEB_ROOT) $(DEB_OUT)
	@echo "Done: $(DEB_OUT)"

install: $(DEB_OUT)
	sudo dpkg -i $(DEB_OUT)
	@echo "Installed to $(INSTALL_PATH)"

endif
