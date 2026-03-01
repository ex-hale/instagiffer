# ---------------------------------------------------------------------------
# Static ImageMagick build for macOS
#
# Builds a fully static, monolithic `magick` binary with all delegate
# libraries compiled from source.  Build artifacts go under build/imagemagick/.
#
# Build tools required (via Homebrew):  pkg-config, cmake, gperf
#
# Usage (called from main Makefile, or standalone):
#   make -f imagemagick.mk          # build everything
#   make -f imagemagick.mk clean    # remove all build artifacts
# ---------------------------------------------------------------------------

# -- Library versions --------------------------------------------------------
ZLIB_VER        := 1.3.1
LIBPNG_VER      := 1.6.43
JPEGTURBO_VER   := 3.0.4
GIFLIB_VER      := 5.2.2
LIBTIFF_VER     := 4.6.0
FREETYPE_VER    := 2.13.3
EXPAT_VER       := 2.6.3
FONTCONFIG_VER  := 2.14.2
IMAGEMAGICK_VER := 7.1.1-41

# -- Download URLs -----------------------------------------------------------
ZLIB_URL        := https://github.com/madler/zlib/releases/download/v$(ZLIB_VER)/zlib-$(ZLIB_VER).tar.gz
LIBPNG_URL      := https://download.sourceforge.net/libpng/libpng-$(LIBPNG_VER).tar.gz
JPEGTURBO_URL   := https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/$(JPEGTURBO_VER)/libjpeg-turbo-$(JPEGTURBO_VER).tar.gz
GIFLIB_URL      := https://sourceforge.net/projects/giflib/files/giflib-$(GIFLIB_VER).tar.gz/download
LIBTIFF_URL     := https://download.osgeo.org/libtiff/tiff-$(LIBTIFF_VER).tar.gz
FREETYPE_URL    := https://download.savannah.gnu.org/releases/freetype/freetype-$(FREETYPE_VER).tar.gz
EXPAT_TAG       := $(subst .,_,$(EXPAT_VER))
EXPAT_URL       := https://github.com/libexpat/libexpat/releases/download/R_$(EXPAT_TAG)/expat-$(EXPAT_VER).tar.gz
FONTCONFIG_URL  := https://www.freedesktop.org/software/fontconfig/release/fontconfig-$(FONTCONFIG_VER).tar.gz
IMAGEMAGICK_URL := https://github.com/ImageMagick/ImageMagick/archive/refs/tags/$(IMAGEMAGICK_VER).tar.gz

# -- Build paths -------------------------------------------------------------
BUILD_ROOT := build/imagemagick
SRC_DIR    := $(BUILD_ROOT)/sources
BUILD_DIR  := $(BUILD_ROOT)/build
PREFIX     := $(abspath $(BUILD_ROOT)/prefix)
STAMPS     := $(BUILD_ROOT)/.stamps
OUT_DIR    := $(BUILD_ROOT)/out

# -- Compiler flags ----------------------------------------------------------
# Target macOS 11.0 (Big Sur) for Intel + Apple Silicon compatibility
export MACOSX_DEPLOYMENT_TARGET := 11.0

CFLAGS_COMMON   := -I$(PREFIX)/include -O2 -mmacosx-version-min=11.0
CPPFLAGS_COMMON := -I$(PREFIX)/include
LDFLAGS_COMMON  := -L$(PREFIX)/lib -mmacosx-version-min=11.0

# pkg-config must only search our static prefix, never Homebrew
export PKG_CONFIG_PATH   := $(PREFIX)/lib/pkgconfig
export PKG_CONFIG_LIBDIR := $(PREFIX)/lib/pkgconfig

# Standard autotools configure flags
CONFIGURE_BASE := --prefix=$(PREFIX) --enable-static --disable-shared --disable-dependency-tracking

NPROC := $(shell sysctl -n hw.ncpu 2>/dev/null || echo 4)

# -- Default target ----------------------------------------------------------
.PHONY: all clean

all: $(OUT_DIR)/magick
	@echo "==> Output ready in $(OUT_DIR)/"

$(OUT_DIR)/magick: $(STAMPS)/imagemagick
	@mkdir -p $(OUT_DIR)/etc/fonts
	@cp $(PREFIX)/bin/magick $(OUT_DIR)/magick
	@cp $(PREFIX)/etc/fonts/fonts.conf $(OUT_DIR)/etc/fonts/
	@cp $(PREFIX)/etc/fonts/local.conf $(OUT_DIR)/etc/fonts/
	@[ -d $(PREFIX)/etc/fonts/conf.d ] && cp -R $(PREFIX)/etc/fonts/conf.d $(OUT_DIR)/etc/fonts/ || true

clean:
	rm -rf $(BUILD_ROOT)

# -- Dependency DAG ----------------------------------------------------------
#
#   zlib ──┬── libpng ──┬── freetype ──┬── fontconfig ──┐
#          │            │              │                │
#          ├── libtiff ─┘       expat ─┘                │
#          │                                            │
#   jpegturbo ──────────────────────────────────────────┤
#   giflib ─────────────────────────────────────────────┤
#                                                       │
#                                              ImageMagick
#

# Directory creation (order-only prerequisites)
$(STAMPS) $(BUILD_DIR) $(SRC_DIR):
	@mkdir -p $@

# ---- 1. zlib ---------------------------------------------------------------
$(STAMPS)/zlib: | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building zlib $(ZLIB_VER)"
	@[ -f $(SRC_DIR)/zlib-$(ZLIB_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/zlib-$(ZLIB_VER).tar.gz "$(ZLIB_URL)"
	@rm -rf $(BUILD_DIR)/zlib-$(ZLIB_VER)
	@tar xzf $(SRC_DIR)/zlib-$(ZLIB_VER).tar.gz -C $(BUILD_DIR)
	cd $(BUILD_DIR)/zlib-$(ZLIB_VER) && \
		CFLAGS="$(CFLAGS_COMMON)" LDFLAGS="$(LDFLAGS_COMMON)" \
		./configure --prefix=$(PREFIX) --static && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@rm -f $(PREFIX)/lib/libz*.dylib
	@touch $@

# ---- 2. libpng (needs zlib) ------------------------------------------------
$(STAMPS)/libpng: $(STAMPS)/zlib | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building libpng $(LIBPNG_VER)"
	@[ -f $(SRC_DIR)/libpng-$(LIBPNG_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/libpng-$(LIBPNG_VER).tar.gz "$(LIBPNG_URL)"
	@rm -rf $(BUILD_DIR)/libpng-$(LIBPNG_VER)
	@tar xzf $(SRC_DIR)/libpng-$(LIBPNG_VER).tar.gz -C $(BUILD_DIR)
	cd $(BUILD_DIR)/libpng-$(LIBPNG_VER) && \
		CFLAGS="$(CFLAGS_COMMON)" CPPFLAGS="$(CPPFLAGS_COMMON)" LDFLAGS="$(LDFLAGS_COMMON)" \
		./configure $(CONFIGURE_BASE) && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@rm -f $(PREFIX)/lib/libpng*.dylib
	@touch $@

# ---- 3. libjpeg-turbo (cmake, no deps) -------------------------------------
$(STAMPS)/jpegturbo: | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building libjpeg-turbo $(JPEGTURBO_VER)"
	@[ -f $(SRC_DIR)/libjpeg-turbo-$(JPEGTURBO_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/libjpeg-turbo-$(JPEGTURBO_VER).tar.gz "$(JPEGTURBO_URL)"
	@rm -rf $(BUILD_DIR)/libjpeg-turbo-$(JPEGTURBO_VER) $(BUILD_DIR)/libjpeg-turbo-build
	@tar xzf $(SRC_DIR)/libjpeg-turbo-$(JPEGTURBO_VER).tar.gz -C $(BUILD_DIR)
	@mkdir -p $(BUILD_DIR)/libjpeg-turbo-build
	cd $(BUILD_DIR)/libjpeg-turbo-build && \
		cmake -G"Unix Makefiles" \
			-DCMAKE_INSTALL_PREFIX=$(PREFIX) \
			-DCMAKE_C_FLAGS="$(CFLAGS_COMMON)" \
			-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
			-DENABLE_SHARED=OFF \
			-DENABLE_STATIC=ON \
			-DCMAKE_INSTALL_LIBDIR=lib \
			$(CURDIR)/$(BUILD_DIR)/libjpeg-turbo-$(JPEGTURBO_VER) && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# ---- 4. giflib (plain Makefile, no configure) -------------------------------
$(STAMPS)/giflib: | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building giflib $(GIFLIB_VER)"
	@[ -f $(SRC_DIR)/giflib-$(GIFLIB_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/giflib-$(GIFLIB_VER).tar.gz "$(GIFLIB_URL)"
	@rm -rf $(BUILD_DIR)/giflib-$(GIFLIB_VER)
	@tar xzf $(SRC_DIR)/giflib-$(GIFLIB_VER).tar.gz -C $(BUILD_DIR)
	cd $(BUILD_DIR)/giflib-$(GIFLIB_VER) && \
		$(MAKE) CFLAGS="$(CFLAGS_COMMON) -std=gnu99 -fPIC -Wall" \
			LDFLAGS="$(LDFLAGS_COMMON)" libgif.a && \
		mkdir -p $(PREFIX)/lib $(PREFIX)/include && \
		cp libgif.a $(PREFIX)/lib/ && \
		cp gif_lib.h $(PREFIX)/include/
	@touch $@

# ---- 5. libtiff (needs zlib + libjpeg) -------------------------------------
$(STAMPS)/libtiff: $(STAMPS)/zlib $(STAMPS)/jpegturbo | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building libtiff $(LIBTIFF_VER)"
	@[ -f $(SRC_DIR)/tiff-$(LIBTIFF_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/tiff-$(LIBTIFF_VER).tar.gz "$(LIBTIFF_URL)"
	@rm -rf $(BUILD_DIR)/tiff-$(LIBTIFF_VER)
	@tar xzf $(SRC_DIR)/tiff-$(LIBTIFF_VER).tar.gz -C $(BUILD_DIR)
	cd $(BUILD_DIR)/tiff-$(LIBTIFF_VER) && \
		CFLAGS="$(CFLAGS_COMMON)" CPPFLAGS="$(CPPFLAGS_COMMON)" LDFLAGS="$(LDFLAGS_COMMON)" \
		./configure $(CONFIGURE_BASE) \
			--disable-webp --disable-lzma --disable-zstd --disable-jbig && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@rm -f $(PREFIX)/lib/libtiff*.dylib
	@touch $@

# ---- 6. freetype (needs zlib + libpng) -------------------------------------
$(STAMPS)/freetype: $(STAMPS)/zlib $(STAMPS)/libpng | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building freetype $(FREETYPE_VER)"
	@[ -f $(SRC_DIR)/freetype-$(FREETYPE_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/freetype-$(FREETYPE_VER).tar.gz "$(FREETYPE_URL)"
	@rm -rf $(BUILD_DIR)/freetype-$(FREETYPE_VER)
	@tar xzf $(SRC_DIR)/freetype-$(FREETYPE_VER).tar.gz -C $(BUILD_DIR)
	cd $(BUILD_DIR)/freetype-$(FREETYPE_VER) && \
		CFLAGS="$(CFLAGS_COMMON)" CPPFLAGS="$(CPPFLAGS_COMMON)" LDFLAGS="$(LDFLAGS_COMMON)" \
		./configure $(CONFIGURE_BASE) \
			--with-zlib=yes --with-png=yes \
			--with-harfbuzz=no --with-bzip2=no --with-brotli=no && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@rm -f $(PREFIX)/lib/libfreetype*.dylib
	@touch $@

# ---- 7. expat (XML parser for fontconfig) -----------------------------------
$(STAMPS)/expat: | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building expat $(EXPAT_VER)"
	@[ -f $(SRC_DIR)/expat-$(EXPAT_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/expat-$(EXPAT_VER).tar.gz "$(EXPAT_URL)"
	@rm -rf $(BUILD_DIR)/expat-$(EXPAT_VER)
	@tar xzf $(SRC_DIR)/expat-$(EXPAT_VER).tar.gz -C $(BUILD_DIR)
	cd $(BUILD_DIR)/expat-$(EXPAT_VER) && \
		CFLAGS="$(CFLAGS_COMMON)" CPPFLAGS="$(CPPFLAGS_COMMON)" LDFLAGS="$(LDFLAGS_COMMON)" \
		./configure $(CONFIGURE_BASE) \
			--without-docbook --without-examples --without-tests && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@rm -f $(PREFIX)/lib/libexpat*.dylib
	@touch $@

# ---- 8. fontconfig (needs freetype + expat; requires gperf) -----------------
$(STAMPS)/fontconfig: $(STAMPS)/freetype $(STAMPS)/expat | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building fontconfig $(FONTCONFIG_VER)"
	@[ -f $(SRC_DIR)/fontconfig-$(FONTCONFIG_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/fontconfig-$(FONTCONFIG_VER).tar.gz "$(FONTCONFIG_URL)"
	@rm -rf $(BUILD_DIR)/fontconfig-$(FONTCONFIG_VER)
	@tar xzf $(SRC_DIR)/fontconfig-$(FONTCONFIG_VER).tar.gz -C $(BUILD_DIR)
	cd $(BUILD_DIR)/fontconfig-$(FONTCONFIG_VER) && \
		CFLAGS="$(CFLAGS_COMMON)" CPPFLAGS="$(CPPFLAGS_COMMON)" LDFLAGS="$(LDFLAGS_COMMON)" \
		./configure $(CONFIGURE_BASE) \
			--sysconfdir=$(PREFIX)/etc \
			--localstatedir=$(PREFIX)/var \
			--disable-docs --disable-cache-build && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@rm -f $(PREFIX)/lib/libfontconfig*.dylib
	@# macOS font directory configuration
	@mkdir -p $(PREFIX)/etc/fonts
	@{ echo '<?xml version="1.0"?>'; \
	   echo '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">'; \
	   echo '<fontconfig>'; \
	   echo '  <dir>/System/Library/Fonts</dir>'; \
	   echo '  <dir>/System/Library/Fonts/Supplemental</dir>'; \
	   echo '  <dir>/Library/Fonts</dir>'; \
	   echo '  <dir>~/Library/Fonts</dir>'; \
	   echo '</fontconfig>'; \
	} > $(PREFIX)/etc/fonts/local.conf
	@touch $@

# ---- 9. ImageMagick (needs all above) --------------------------------------
IM_DEPS := $(STAMPS)/zlib $(STAMPS)/libpng $(STAMPS)/jpegturbo \
           $(STAMPS)/giflib $(STAMPS)/libtiff $(STAMPS)/freetype \
           $(STAMPS)/expat $(STAMPS)/fontconfig

$(STAMPS)/imagemagick: $(IM_DEPS) | $(STAMPS) $(BUILD_DIR) $(SRC_DIR)
	@echo "==> Building ImageMagick $(IMAGEMAGICK_VER)"
	@[ -f $(SRC_DIR)/ImageMagick-$(IMAGEMAGICK_VER).tar.gz ] || \
		curl -fSL -o $(SRC_DIR)/ImageMagick-$(IMAGEMAGICK_VER).tar.gz "$(IMAGEMAGICK_URL)"
	@rm -rf $(BUILD_DIR)/ImageMagick-$(IMAGEMAGICK_VER)
	@tar xzf $(SRC_DIR)/ImageMagick-$(IMAGEMAGICK_VER).tar.gz -C $(BUILD_DIR)
	cd $(BUILD_DIR)/ImageMagick-$(IMAGEMAGICK_VER) && \
		CFLAGS="$(CFLAGS_COMMON)" CPPFLAGS="$(CPPFLAGS_COMMON)" LDFLAGS="$(LDFLAGS_COMMON)" \
		./configure \
			--prefix=$(PREFIX) \
			--enable-static --disable-shared \
			--disable-dependency-tracking \
			--without-modules \
			--enable-zero-configuration \
			--disable-installed \
			--disable-openmp \
			--with-magick-plus-plus=no \
			--with-perl=no \
			--disable-docs \
			--with-zlib=yes \
			--with-png=yes \
			--with-jpeg=yes \
			--with-tiff=yes \
			--with-gif=yes \
			--with-freetype=yes \
			--with-fontconfig=yes \
			--enable-hdri=yes \
			--with-quantum-depth=16 \
			--without-x \
			--without-bzlib \
			--without-lzma \
			--without-zstd \
			--without-webp \
			--without-heic \
			--without-jxl \
			--without-raw \
			--without-openjp2 \
			--without-lcms \
			--without-pango \
			--without-djvu \
			--without-wmf \
			--without-openexr \
			--without-gslib \
			--without-gvc \
			--without-rsvg \
			--without-xml \
			--without-dps \
			--without-fftw \
			--without-flif \
			--without-fpx \
			--without-jbig && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@echo "==> Static magick binary built successfully"
	@$(PREFIX)/bin/magick --version
	@touch $@
