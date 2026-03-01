# imagemagick.mk — Static ImageMagick build for macOS
#
# Produces a single self-contained `magick` binary with all delegate libraries
# (zlib, libpng, libjpeg-turbo, giflib, libtiff, freetype, fontconfig) built
# from source and statically linked.
#
# Usage:  make -f imagemagick.mk          (build)
#         make -f imagemagick.mk clean    (remove all artifacts)

ZLIB_VER        := 1.3.1
LIBPNG_VER      := 1.6.43
JPEGTURBO_VER   := 3.0.4
GIFLIB_VER      := 5.2.2
LIBTIFF_VER     := 4.6.0
FREETYPE_VER    := 2.13.3
EXPAT_VER       := 2.6.3
FONTCONFIG_VER  := 2.14.2
IMAGEMAGICK_VER := 7.1.1-41

ZLIB_URL        := https://github.com/madler/zlib/releases/download/v$(ZLIB_VER)/zlib-$(ZLIB_VER).tar.gz
LIBPNG_URL      := https://download.sourceforge.net/libpng/libpng-$(LIBPNG_VER).tar.gz
JPEGTURBO_URL   := https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/$(JPEGTURBO_VER)/libjpeg-turbo-$(JPEGTURBO_VER).tar.gz
GIFLIB_URL      := https://sourceforge.net/projects/giflib/files/giflib-$(GIFLIB_VER).tar.gz/download
LIBTIFF_URL     := https://download.osgeo.org/libtiff/tiff-$(LIBTIFF_VER).tar.gz
FREETYPE_URL    := https://download.savannah.gnu.org/releases/freetype/freetype-$(FREETYPE_VER).tar.gz
EXPAT_URL       := https://github.com/libexpat/libexpat/releases/download/R_$(subst .,_,$(EXPAT_VER))/expat-$(EXPAT_VER).tar.gz
FONTCONFIG_URL  := https://www.freedesktop.org/software/fontconfig/release/fontconfig-$(FONTCONFIG_VER).tar.gz
IMAGEMAGICK_URL := https://github.com/ImageMagick/ImageMagick/archive/refs/tags/$(IMAGEMAGICK_VER).tar.gz

BUILD   := build/imagemagick
SRC     := $(BUILD)/sources
OBJ     := $(BUILD)/build
PREFIX  := $(abspath $(BUILD)/prefix)
STAMPS  := $(BUILD)/.stamps
OUT     := $(BUILD)/out
DIRS    := $(STAMPS) $(OBJ) $(SRC)

export MACOSX_DEPLOYMENT_TARGET := 11.0
export PKG_CONFIG_PATH          := $(PREFIX)/lib/pkgconfig
export PKG_CONFIG_LIBDIR        := $(PREFIX)/lib/pkgconfig

NPROC  := $(shell sysctl -n hw.ncpu 2>/dev/null || echo 4)
CFLG   := -I$(PREFIX)/include -O2 -mmacosx-version-min=11.0
LFLG   := -L$(PREFIX)/lib -mmacosx-version-min=11.0

# Env prefix for all configure/make invocations
ENV    := CFLAGS="$(CFLG)" CPPFLAGS="-I$(PREFIX)/include" LDFLAGS="$(LFLG)"

# Standard autotools configure flags
CONF   := --prefix=$(PREFIX) --enable-static --disable-shared --disable-dependency-tracking

# Download tarball if absent:  @$(call fetch,name-ver.tar.gz,url)
fetch = [ -f $(SRC)/$(1) ] || curl -fSL -o $(SRC)/$(1) "$(2)"

# Clean-extract into OBJ:     @$(call extract,name-ver)
extract = rm -rf $(OBJ)/$(1) && tar xzf $(SRC)/$(1).tar.gz -C $(OBJ)

.PHONY: all clean

all: $(OUT)/magick
	@echo "==> Output ready in $(OUT)/"

$(OUT)/magick: $(STAMPS)/imagemagick
	@mkdir -p $(OUT)/etc/fonts
	@cp $(PREFIX)/bin/magick $(OUT)/magick
	@cp $(PREFIX)/etc/fonts/fonts.conf $(PREFIX)/etc/fonts/local.conf $(OUT)/etc/fonts/
	@[ -d $(PREFIX)/etc/fonts/conf.d ] && cp -R $(PREFIX)/etc/fonts/conf.d $(OUT)/etc/fonts/ || true

clean:
	rm -rf $(BUILD)

$(DIRS):
	@mkdir -p $@

# zlib
$(STAMPS)/zlib: | $(DIRS)
	@echo "==> zlib $(ZLIB_VER)"
	@$(call fetch,zlib-$(ZLIB_VER).tar.gz,$(ZLIB_URL))
	@$(call extract,zlib-$(ZLIB_VER))
	cd $(OBJ)/zlib-$(ZLIB_VER) && $(ENV) \
		./configure --prefix=$(PREFIX) --static && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# libpng (zlib)
$(STAMPS)/libpng: $(STAMPS)/zlib | $(DIRS)
	@echo "==> libpng $(LIBPNG_VER)"
	@$(call fetch,libpng-$(LIBPNG_VER).tar.gz,$(LIBPNG_URL))
	@$(call extract,libpng-$(LIBPNG_VER))
	cd $(OBJ)/libpng-$(LIBPNG_VER) && $(ENV) \
		./configure $(CONF) && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# libjpeg-turbo (cmake)
$(STAMPS)/jpegturbo: | $(DIRS)
	@echo "==> libjpeg-turbo $(JPEGTURBO_VER)"
	@$(call fetch,libjpeg-turbo-$(JPEGTURBO_VER).tar.gz,$(JPEGTURBO_URL))
	@$(call extract,libjpeg-turbo-$(JPEGTURBO_VER))
	@rm -rf $(OBJ)/libjpeg-turbo-build && mkdir -p $(OBJ)/libjpeg-turbo-build
	cd $(OBJ)/libjpeg-turbo-build && cmake -G"Unix Makefiles" \
		-DCMAKE_INSTALL_PREFIX=$(PREFIX) -DCMAKE_INSTALL_LIBDIR=lib \
		-DCMAKE_C_FLAGS="$(CFLG)" -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
		-DENABLE_SHARED=OFF -DENABLE_STATIC=ON \
		$(CURDIR)/$(OBJ)/libjpeg-turbo-$(JPEGTURBO_VER) && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# giflib (plain Makefile)
$(STAMPS)/giflib: | $(DIRS)
	@echo "==> giflib $(GIFLIB_VER)"
	@$(call fetch,giflib-$(GIFLIB_VER).tar.gz,$(GIFLIB_URL))
	@$(call extract,giflib-$(GIFLIB_VER))
	cd $(OBJ)/giflib-$(GIFLIB_VER) && \
		$(MAKE) CFLAGS="$(CFLG) -std=gnu99 -fPIC -Wall" libgif.a && \
		cp libgif.a $(PREFIX)/lib/ && cp gif_lib.h $(PREFIX)/include/
	@touch $@

# libtiff (zlib, jpegturbo)
$(STAMPS)/libtiff: $(STAMPS)/zlib $(STAMPS)/jpegturbo | $(DIRS)
	@echo "==> libtiff $(LIBTIFF_VER)"
	@$(call fetch,tiff-$(LIBTIFF_VER).tar.gz,$(LIBTIFF_URL))
	@$(call extract,tiff-$(LIBTIFF_VER))
	cd $(OBJ)/tiff-$(LIBTIFF_VER) && $(ENV) \
		./configure $(CONF) --disable-webp --disable-lzma --disable-zstd --disable-jbig && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# freetype (zlib, libpng)
$(STAMPS)/freetype: $(STAMPS)/zlib $(STAMPS)/libpng | $(DIRS)
	@echo "==> freetype $(FREETYPE_VER)"
	@$(call fetch,freetype-$(FREETYPE_VER).tar.gz,$(FREETYPE_URL))
	@$(call extract,freetype-$(FREETYPE_VER))
	cd $(OBJ)/freetype-$(FREETYPE_VER) && $(ENV) \
		./configure $(CONF) \
			--with-zlib=yes --with-png=yes \
			--with-harfbuzz=no --with-bzip2=no --with-brotli=no && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# expat
$(STAMPS)/expat: | $(DIRS)
	@echo "==> expat $(EXPAT_VER)"
	@$(call fetch,expat-$(EXPAT_VER).tar.gz,$(EXPAT_URL))
	@$(call extract,expat-$(EXPAT_VER))
	cd $(OBJ)/expat-$(EXPAT_VER) && $(ENV) \
		./configure $(CONF) --without-docbook --without-examples --without-tests && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# fontconfig (freetype, expat — requires gperf at build time)
$(STAMPS)/fontconfig: $(STAMPS)/freetype $(STAMPS)/expat | $(DIRS)
	@echo "==> fontconfig $(FONTCONFIG_VER)"
	@$(call fetch,fontconfig-$(FONTCONFIG_VER).tar.gz,$(FONTCONFIG_URL))
	@$(call extract,fontconfig-$(FONTCONFIG_VER))
	cd $(OBJ)/fontconfig-$(FONTCONFIG_VER) && $(ENV) \
		./configure $(CONF) \
			--sysconfdir=$(PREFIX)/etc --localstatedir=$(PREFIX)/var \
			--disable-docs --disable-cache-build && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@printf '<?xml version="1.0"?>\n\
	<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n\
	<fontconfig>\n\
	  <dir>/System/Library/Fonts</dir>\n\
	  <dir>/System/Library/Fonts/Supplemental</dir>\n\
	  <dir>/Library/Fonts</dir>\n\
	  <dir>~/Library/Fonts</dir>\n\
	</fontconfig>\n' > $(PREFIX)/etc/fonts/local.conf
	@touch $@

# ImageMagick (everything above)
IM_DEPS := $(addprefix $(STAMPS)/,zlib libpng jpegturbo giflib libtiff freetype expat fontconfig)

$(STAMPS)/imagemagick: $(IM_DEPS) | $(DIRS)
	@echo "==> ImageMagick $(IMAGEMAGICK_VER)"
	@$(call fetch,ImageMagick-$(IMAGEMAGICK_VER).tar.gz,$(IMAGEMAGICK_URL))
	@$(call extract,ImageMagick-$(IMAGEMAGICK_VER))
	cd $(OBJ)/ImageMagick-$(IMAGEMAGICK_VER) && $(ENV) \
		./configure --prefix=$(PREFIX) \
			--enable-static --disable-shared --disable-dependency-tracking \
			--without-modules --enable-zero-configuration \
			--disable-installed --disable-openmp --disable-docs \
			--with-magick-plus-plus=no --with-perl=no \
			--with-zlib=yes   --with-png=yes      --with-jpeg=yes \
			--with-tiff=yes   --with-gif=yes      --with-freetype=yes \
			--with-fontconfig=yes --enable-hdri=yes --with-quantum-depth=16 \
			--without-x       --without-bzlib     --without-lzma \
			--without-zstd    --without-webp      --without-heic \
			--without-jxl     --without-raw       --without-openjp2 \
			--without-lcms    --without-pango     --without-djvu \
			--without-wmf     --without-openexr   --without-gslib \
			--without-gvc     --without-rsvg      --without-xml \
			--without-dps     --without-fftw      --without-flif \
			--without-fpx     --without-jbig && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@$(PREFIX)/bin/magick --version
	@touch $@
