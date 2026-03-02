VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

VERSION := $(shell python3 -c "import instagiffer; print(instagiffer.__version__)")

TEST_VIDEO_URLS := \
	https://www.youtube.com/watch?v=aqz-KE-bpKQ \
	https://www.youtube.com/watch?v=L_uXZEkhlZU

.PHONY: init run test test-app test-videos lint format clean deps dist install uninstall

init: $(VENV)/bin/activate

$(VENV)/bin/activate: pyproject.toml
	python3 -m venv $(VENV)
	$(PIP) install -e ".[dev]"
	@echo "\nDone. Activate with: source $(VENV)/bin/activate"

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
			yt-dlp -f "worst[ext=mp4]/worst" -o "test/test_data/test_video_$$i.mp4" "$$url"; \
		fi; \
		i=$$((i + 1)); \
	done

test: init format lint test-videos
	$(PYTHON) -m pytest

test-app: install test-videos
	$(PYTHON) -m pytest --app-package=$(INSTALL_PATH)

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

deps: init
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
	@echo "macOS dependencies ready in deps/mac/"

$(APP_PATH): init
	@echo "Building Mac release with PyInstaller"
	$(PYTHON) -m PyInstaller release/Instagiffer.spec --distpath dist --workpath build/pyinstaller --noconfirm
	codesign --force --deep --sign - $(APP_PATH)

dist: $(APP_PATH)
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

install: $(APP_PATH)
	@rm -rf $(INSTALL_PATH)
	cp -R $(APP_PATH) $(INSTALL_PATH)
	@echo "Installed to $(INSTALL_PATH)"

else ifeq ($(OS),Windows_NT)

deps:
	@echo "Windows deps: place binaries in deps/win/ manually (see README)"

dist: init deps format lint test
	python release/setup-win-cx_freeze.py build
	del instagiffer*setup.exe 2>NUL || true
	"C:\Program Files (x86)\Inno Setup 5\ISCC.exe" release/installer.iss \
		/dMyAppVersion=$(VERSION)
	@echo "Built instagiffer-$(VERSION)-setup.exe"

endif
