VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

VERSION := $(shell perl -ne 'print "$$1" if /INSTAGIFFER_VERSION\s*=\s*"([0-9.]+)"/' instagiffer.py)
PRERELEASE := $(shell perl -ne 'print "$$1" if /INSTAGIFFER_PRERELEASE\s*=\s*"([^"]*)"/' instagiffer.py)
MAC_APP_PATH := dist/Instagiffer.app

.PHONY: setup test lint format run clean \
        mac_deps \
        mac_app mac_dmg mac_pkg mac_release \
        win_exe win_installer win_portable win_release

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

setup: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt
	@echo "\nDone. Activate with: source $(VENV)/bin/activate"

test: setup
	$(PYTHON) -m pytest test_instagiffer.py -v --tb=short

lint: setup
	$(PYTHON) -m pylint instagiffer.py main.py test_instagiffer.py

format: setup
	$(PYTHON) -m black instagiffer.py main.py test_instagiffer.py

run: setup
	$(PYTHON) main.py

# ---------------------------------------------------------------------------
# macOS dependency downloads (skip if already present)
# ---------------------------------------------------------------------------

mac_deps:
	@mkdir -p deps/mac
	@if [ -f deps/mac/ffmpeg ]; then \
		echo "ffmpeg already exists, skipping"; \
	else \
		echo "Downloading ffmpeg..."; \
		curl -L -o deps/mac/ffmpeg.zip "https://evermeet.cx/ffmpeg/getrelease/zip"; \
		unzip -o deps/mac/ffmpeg.zip -d deps/mac/ && rm deps/mac/ffmpeg.zip; \
		chmod +x deps/mac/ffmpeg; \
	fi
	@if [ -f deps/mac/yt-dlp ]; then \
		echo "yt-dlp already exists, skipping"; \
	else \
		echo "Downloading yt-dlp..."; \
		curl -L -o deps/mac/yt-dlp "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"; \
		chmod +x deps/mac/yt-dlp; \
	fi
	@if [ -f deps/mac/gifsicle ]; then \
		echo "gifsicle already exists, skipping"; \
	else \
		if command -v gifsicle >/dev/null 2>&1; then \
			echo "Copying gifsicle from Homebrew..."; \
			cp "$$(which gifsicle)" deps/mac/gifsicle; \
			chmod +x deps/mac/gifsicle; \
		else \
			echo "WARNING: gifsicle not found. Install with: brew install gifsicle"; \
		fi; \
	fi
	@echo "macOS dependencies ready in deps/mac/"

# ---------------------------------------------------------------------------
# macOS release build (py2app)
# ---------------------------------------------------------------------------

mac_app: setup
	$(PYTHON) -m compileall instagiffer.py
	@echo "Building Mac release with py2app"
	$(PYTHON) setup-mac-py2app.py py2app

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
	python setup-win-cx_freeze.py build
	rmdir /S /Q build\exe.win32-2.7\tk\demos 2>NUL || true

win_installer: win_exe
	del instagiffer*setup.exe 2>NUL || true
	"C:\Program Files (x86)\Inno Setup 5\ISCC.exe" installer.iss \
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

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache instagiffer-event.log
	rm -rf dist/ build/ *.pyc *.dmg *.pkg
