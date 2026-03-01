VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

VERSION := $(shell python3 -c "print(next(l.split('\"')[1] for l in open('instagiffer.py') if l.startswith('INSTAGIFFER_VERSION')))")
PRERELEASE := $(shell python3 -c "print(next(l.split('\"')[1] for l in open('instagiffer.py') if l.startswith('INSTAGIFFER_PRERELEASE')))")

TEST_VIDEO_URLS := https://www.youtube.com/watch?v=aqz-KE-bpKQ https://www.youtube.com/watch?v=L_uXZEkhlZU

MAC_APP_PATH   := dist/Instagiffer.app
MAC_MAGICK_OUT := build/imagemagick/out
MAC_FFMPEG_URL := https://evermeet.cx/ffmpeg/getrelease/zip
MAC_YTDLP_URL  := https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos

.PHONY: setup test test-videos lint format run clean \
        mac_deps mac_deps_clean \
        mac_app mac_dmg mac_pkg mac_release \
        win_exe win_installer win_portable win_release

clean:
	rm -rf $(VENV) __pycache__ test/__pycache__ .pytest_cache *.egg-info instagiffer-event.log
	rm -rf dist/ build/ deps/ *.pyc *.dmg *.pkg
	rm -rf test/test_data/

setup: $(VENV)/bin/activate mac_deps

$(VENV)/bin/activate: pyproject.toml
	python3 -m venv $(VENV)
	$(PIP) install -e ".[dev]"
	@echo "\nDone. Activate with: source $(VENV)/bin/activate"

test-videos:
	@mkdir -p test/test_data
	@i=1; for url in $(TEST_VIDEO_URLS); do \
		if [ ! -f "test/test_data/test_video_$$i.mp4" ]; then \
			yt-dlp -f "worst[ext=mp4]/worst" -o "test/test_data/test_video_$$i.mp4" "$$url"; \
		fi; \
		i=$$((i + 1)); \
	done

test: setup test-videos
	@rm -f test/test_data/*.gif
	$(PYTHON) -m pytest test/test_instagiffer.py -v --tb=short

lint: setup
	$(PYTHON) -m pylint instagiffer.py main.py test/test_instagiffer.py test/instagiffer_automation.py

format: setup
	$(PYTHON) -m black instagiffer.py main.py test/test_instagiffer.py test/instagiffer_automation.py

run: setup
	$(PYTHON) main.py

# macOS dependencies

mac_deps:
	@command -v brew >/dev/null || (echo "Error: Homebrew required — https://brew.sh" && exit 1)
	@for pkg in pkg-config cmake gperf gifsicle; do \
		brew list $$pkg >/dev/null 2>&1 || brew install $$pkg; \
	done
	$(MAKE) -f imagemagick.mk
	@mkdir -p deps/mac
	@cp -R $(MAC_MAGICK_OUT)/* deps/mac/
	@[ -f deps/mac/ffmpeg ]   || (curl -fSL -o deps/mac/ffmpeg.zip "$(MAC_FFMPEG_URL)" && unzip -o deps/mac/ffmpeg.zip -d deps/mac/ && rm deps/mac/ffmpeg.zip && chmod +x deps/mac/ffmpeg)
	@[ -f deps/mac/yt-dlp ]   || (curl -fSL -o deps/mac/yt-dlp "$(MAC_YTDLP_URL)" && chmod +x deps/mac/yt-dlp)
	@[ -f deps/mac/gifsicle ] || cp "$$(which gifsicle)" deps/mac/gifsicle
	@echo "macOS dependencies ready in deps/mac/"

mac_deps_clean:
	$(MAKE) -f imagemagick.mk clean
	rm -rf deps/mac

# macOS release build (py2app)

mac_app: setup
	$(PYTHON) -m compileall instagiffer.py
	@echo "Building Mac release with py2app"
	$(PYTHON) release/setup-mac-py2app.py py2app

mac_dmg: mac_app
	@echo "Building DMG installer (v$(VERSION)$(PRERELEASE))"
	rm -f Instagiffer-$(VERSION)$(PRERELEASE).sparseimage Instagiffer-$(VERSION)$(PRERELEASE).dmg
	cp Instagiffer.sparseimage Instagiffer-$(VERSION)$(PRERELEASE).sparseimage
	hdiutil attach Instagiffer-$(VERSION)$(PRERELEASE).sparseimage
	cp -a $(MAC_APP_PATH) /Volumes/Instagiffer/
	@echo "Position the icon, then press Enter..."
	@read _unused
	hdiutil detach /Volumes/Instagiffer
	hdiutil convert Instagiffer-$(VERSION)$(PRERELEASE).sparseimage \
		-format UDZO -o Instagiffer-$(VERSION)$(PRERELEASE).dmg -imagekey zlib-level=9
	rm Instagiffer-$(VERSION)$(PRERELEASE).sparseimage

mac_pkg: mac_app
	productbuild --component $(MAC_APP_PATH) /Applications Instagiffer-$(VERSION)$(PRERELEASE).pkg

mac_release: mac_dmg mac_pkg
	@echo "Built Instagiffer-$(VERSION)$(PRERELEASE).dmg and .pkg"

# ---------------------------------------------------------------------------
# Windows release build (cx_Freeze + Inno Setup)
# ---------------------------------------------------------------------------

win_exe:
	rd /S /Q build 2>NUL || true
	python release/setup-win-cx_freeze.py build
	rmdir /S /Q build\exe.win32-2.7\tk\demos 2>NUL || true

win_installer: win_exe
	del instagiffer*setup.exe 2>NUL || true
	"C:\Program Files (x86)\Inno Setup 5\ISCC.exe" release/installer.iss \
		/dMyAppVersion=$(VERSION)$(PRERELEASE)

win_portable: win_installer
	"C:\Program Files (x86)\Instagiffer\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES || true
	instagiffer-$(VERSION)$(PRERELEASE)-setup.exe /SP- /SILENT /SUPPRESSMSGBOXES
	xcopy /Y /I /S "C:\Program Files (x86)\Instagiffer" instagiffer-$(VERSION)$(PRERELEASE)
	del .\instagiffer-$(VERSION)$(PRERELEASE)\unins*
	copy /Y instagiffer-event.log .\instagiffer-$(VERSION)$(PRERELEASE)
	"C:\Program Files\7-Zip\7z.exe" a -tzip \
		instagiffer-$(VERSION)$(PRERELEASE)-portable.zip \
		instagiffer-$(VERSION)$(PRERELEASE)
	rmdir /S /Q instagiffer-$(VERSION)$(PRERELEASE)

win_release: win_installer win_portable
	@echo "Built installer and portable zip for v$(VERSION)$(PRERELEASE)"


