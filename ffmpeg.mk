# ffmpeg.mk — Static ffmpeg build for macOS (Apple Silicon / x86_64)
#
# Produces a single self-contained `ffmpeg` binary with libx264 statically linked.
#
# Usage:  make -f ffmpeg.mk		  (build)
#		 make -f ffmpeg.mk clean	(remove all artifacts)

NASM_VER   := 2.16.03
X264_URL   := https://code.videolan.org/videolan/x264/-/archive/stable/x264-stable.tar.gz
FFMPEG_VER := 9.1
FFMPEG_URL := https://ffmpeg.org/releases/ffmpeg-$(FFMPEG_VER).tar.xz

BUILD   := build/ffmpeg
SRC	 := $(BUILD)/sources
OBJ	 := $(BUILD)/build
PREFIX  := $(abspath $(BUILD)/prefix)
STAMPS  := $(BUILD)/.stamps
OUT	 := $(BUILD)/out
DIRS	:= $(STAMPS) $(OBJ) $(SRC)

export MACOSX_DEPLOYMENT_TARGET := 11.0
export PKG_CONFIG_PATH		  := $(PREFIX)/lib/pkgconfig
export PKG_CONFIG_LIBDIR		:= $(PREFIX)/lib/pkgconfig

NPROC  := $(shell sysctl -n hw.ncpu 2>/dev/null || echo 4)
CFLG   := -I$(PREFIX)/include -O2 -mmacosx-version-min=11.0
LFLG   := -L$(PREFIX)/lib -mmacosx-version-min=11.0

# Env prefix for all configure/make invocations
ENV	:= CFLAGS="$(CFLG)" CPPFLAGS="-I$(PREFIX)/include" LDFLAGS="$(LFLG)"

# Download tarball if absent:  @$(call fetch,name.tar.gz,url)
fetch = [ -f $(SRC)/$(1) ] || curl -fSL -o $(SRC)/$(1) "$(2)"

# Clean-extract into OBJ (auto-detects .tar.gz / .tar.xz):  @$(call extract,name)
extract = rm -rf $(OBJ)/$(1) && tar xf $(SRC)/$(1).tar.* -C $(OBJ)

.PHONY: all clean

all: $(OUT)/ffmpeg
	@echo "==> Output ready in $(OUT)/"

$(OUT)/ffmpeg: $(STAMPS)/ffmpeg
	@mkdir -p $(OUT)
	@cp $(PREFIX)/bin/ffmpeg $(OUT)/ffmpeg
	@chmod +x $(OUT)/ffmpeg

clean:
	rm -rf $(BUILD)

$(DIRS):
	@mkdir -p $@

# nasm (assembler required by x264 on x86_64; harmless on arm64)
$(STAMPS)/nasm: | $(DIRS)
	@echo "==> nasm $(NASM_VER)"
	@$(call fetch,nasm-$(NASM_VER).tar.gz,https://www.nasm.us/pub/nasm/releasebuilds/$(NASM_VER)/nasm-$(NASM_VER).tar.gz)
	@$(call extract,nasm-$(NASM_VER))
	cd $(OBJ)/nasm-$(NASM_VER) && $(ENV) \
		./configure --prefix=$(PREFIX) && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# x264 (GPL H.264 encoder)
$(STAMPS)/x264: $(STAMPS)/nasm | $(DIRS)
	@echo "==> x264 stable"
	@$(call fetch,x264-stable.tar.gz,$(X264_URL))
	@$(call extract,x264-stable)
	cd $(OBJ)/x264-stable && $(ENV) \
		PATH="$(PREFIX)/bin:$$PATH" ./configure \
			--prefix=$(PREFIX) \
			--enable-static --disable-shared \
			--disable-cli \
			--disable-opencl && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@touch $@

# ffmpeg (depends on x264)
$(STAMPS)/ffmpeg: $(STAMPS)/x264 | $(DIRS)
	@echo "==> ffmpeg $(FFMPEG_VER)"
	@$(call fetch,ffmpeg-$(FFMPEG_VER).tar.xz,$(FFMPEG_URL))
	@$(call extract,ffmpeg-$(FFMPEG_VER))
	cd $(OBJ)/ffmpeg-$(FFMPEG_VER) && $(ENV) \
		./configure \
			--prefix=$(PREFIX) \
			--enable-static --disable-shared \
			--disable-doc \
			--disable-ffplay --disable-ffprobe \
			--enable-gpl \
			--enable-libx264 \
			--extra-cflags="$(CFLG)" \
			--extra-ldflags="$(LFLG)" \
			--pkg-config-flags="--static" && \
		$(MAKE) -j$(NPROC) && $(MAKE) install
	@$(PREFIX)/bin/ffmpeg -version
	@touch $@