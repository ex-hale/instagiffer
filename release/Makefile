VENV := .venv

ifeq ($(OS),Windows_NT)
    PYTHON     := $(VENV)/Scripts/python
    PIP        := $(VENV)/Scripts/pip
    PYTHON_CMD := python
    VENV_STAMP := $(VENV)/Scripts/activate
else
    PYTHON     := $(VENV)/bin/python3
    PIP        := $(VENV)/bin/pip
    PYTHON_CMD := python3
    VENV_STAMP := $(VENV)/bin/activate
endif

VERSION := $(shell grep -m1 '__version__' instagiffer.py | awk -F'"' '{print $$2}')

TEST_VIDEO_URLS := \
	https://www.youtube.com/watch?v=aqz-KE-bpKQ \
	https://www.youtube.com/watch?v=L_uXZEkhlZU

.PHONY: init run test test-app test-videos lint format clean

init: $(VENV_STAMP)

$(VENV_STAMP): pyproject.toml
	$(PYTHON_CMD) -m venv $(VENV)
	$(PIP) install -e ".[dev]"
	@echo "Done. Activate with: source $(VENV_STAMP)"

run: init
	$(PYTHON) main.py

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

ifeq ($(shell uname -s),Darwin)

APP_PATH     := dist/Instagiffer.app
INSTALL_PATH := /Applications/Instagiffer.app
MAGICK_OUT   := build/imagemagick/out
FFMPEG_URL   := https://evermeet.cx/ffmpeg/getrelease/zip
YTDLP_URL    := https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos
YTDLP        := deps/mac/yt-dlp

DEPS_STAMP := build/.deps-stamp
DIST_STAMP := build/.dist-stamp

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
	@[ -f deps/mac/ffmpeg ]   || (curl -fSL -o deps/mac/ffmpeg.zip "$(FFMPEG_URL)" && unzip -o deps/mac/ffmpeg.zip -d deps/mac/ && rm deps/mac/ffmpeg.zip && chmod +x deps/mac/ffmpeg)
	@[ -f deps/mac/yt-dlp ]   || (curl -fSL -o deps/mac/yt-dlp "$(YTDLP_URL)" && chmod +x deps/mac/yt-dlp)
	@[ -f deps/mac/gifsicle ] || cp "$$(which gifsicle)" deps/mac/gifsicle
	@touch $@
	@echo "macOS dependencies ready in deps/mac/"

$(DIST_STAMP): $(VENV_STAMP) instagiffer.py main.py instagiffer.conf $(DEPS_STAMP)
	@echo "Building Mac release with PyInstaller"
	$(PYTHON) -m PyInstaller release/Instagiffer-mac.spec --distpath dist --workpath build/pyinstaller --noconfirm
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

else ifeq ($(OS),Windows_NT)

APP_PATH     := dist/Instagiffer
INSTALL_PATH := C:/Program Files/Instagiffer/Instagiffer.exe
ISCC         := $(or $(wildcard C:/Program Files (x86)/Inno Setup 6/ISCC.exe),$(LOCALAPPDATA)/Programs/Inno Setup 6/ISCC.exe)
SEVENZIP     := C:/Program Files/7-Zip/7z.exe
MAGICK_VER   := 7.1.2-15
MAGICK_URL   := https://imagemagick.org/archive/binaries/ImageMagick-$(MAGICK_VER)-portable-Q16-x64.7z
FFMPEG_URL   := https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
YTDLP_URL    := https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
YTDLP        := deps/win/yt-dlp.exe
GIFSICLE_URL := https://eternallybored.org/misc/gifsicle/releases/gifsicle-1.95-win64.zip

DEPS_STAMP    := build/.deps-stamp
DIST_STAMP    := build/.dist-stamp
INSTALL_STAMP := build/.install-stamp

deps: $(DEPS_STAMP)
$(DEPS_STAMP): $(VENV_STAMP)
	$(PIP) install -e ".[build-win,test-win]"
	@mkdir -p deps/win build
	@[ -f deps/win/magick.exe ] || ( \
		curl -fSL -o build/magick-win.7z "$(MAGICK_URL)" && \
		"$(SEVENZIP)" e build/magick-win.7z -odeps/win -y "magick.exe" && \
		rm build/magick-win.7z )
	@[ -f deps/win/ffmpeg.exe ] || ( \
		curl -fSL -o build/ffmpeg-win.zip "$(FFMPEG_URL)" && \
		mkdir -p build/ffmpeg-tmp && \
		unzip -o build/ffmpeg-win.zip -d build/ffmpeg-tmp && \
		find build/ffmpeg-tmp -name ffmpeg.exe -exec cp {} deps/win/ \; && \
		rm -rf build/ffmpeg-win.zip build/ffmpeg-tmp )
	@[ -f deps/win/yt-dlp.exe ] || curl -fSL -o deps/win/yt-dlp.exe "$(YTDLP_URL)"
	@[ -f deps/win/gifsicle.exe ] || ( \
		curl -fSL -o build/gifsicle-win.zip "$(GIFSICLE_URL)" && \
		unzip -jo build/gifsicle-win.zip "*.exe" -d deps/win/ && \
		rm build/gifsicle-win.zip )
	@touch $@
	@echo "Windows dependencies ready in deps/win/"

$(DIST_STAMP): $(VENV_STAMP) instagiffer.py main.py instagiffer.conf $(DEPS_STAMP)
	@echo "Building Windows release with PyInstaller"
	$(PYTHON) -m PyInstaller release/Instagiffer-win.spec --distpath dist --workpath build/pyinstaller --noconfirm
	@touch $@

dist: $(DIST_STAMP)
	@rm -f dist/instagiffer-$(VERSION)-setup.exe
	"$(ISCC)" release/installer.iss //dMyAppVersion=$(VERSION)
	@SIZE=$$(stat -c%s "dist/instagiffer-$(VERSION)-setup.exe"); echo "Built dist/instagiffer-$(VERSION)-setup.exe ($$(( SIZE / 1048576 ))MB)"

install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(DIST_STAMP) release/installer.iss
	@rm -f dist/instagiffer-$(VERSION)-setup.exe
	"$(ISCC)" release/installer.iss //dMyAppVersion=$(VERSION)
	MSYS_NO_PATHCONV=1 dist/instagiffer-$(VERSION)-setup.exe /VERYSILENT /SUPPRESSMSGBOXES
	@touch $@
	@echo "Installed to $(INSTALL_PATH)"

endif
