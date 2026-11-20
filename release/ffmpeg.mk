FFMPEG_VERSION := 9.1
FFMPEG_TARBALL := ffmpeg-$(FFMPEG_VERSION).tar.xz
FFMPEG_URL     := https://ffmpeg.org/releases/$(FFMPEG_TARBALL)
FFMPEG_SRC     := deps/build/ffmpeg-$(FFMPEG_VERSION)
FFMPEG_OUT     := deps/build/ffmpeg-out

# Static build so the binary is self-contained in deps/mac/
FFMPEG_CONFIGURE := \
    ./configure \
    --prefix=$(abspath $(FFMPEG_OUT)) \
    --enable-static \
    --disable-shared \
    --disable-doc \
    --disable-ffplay \
    --disable-ffprobe \
    --enable-gpl \
    --enable-version3 \
	--enable-libx264

$(FFMPEG_OUT)/bin/ffmpeg: $(FFMPEG_SRC)/configure
    cd $(FFMPEG_SRC) && $(FFMPEG_CONFIGURE)
    $(MAKE) -C $(FFMPEG_SRC) -j$$(sysctl -n hw.ncpu)
    $(MAKE) -C $(FFMPEG_SRC) install
    @touch $@

$(FFMPEG_SRC)/configure:
    @mkdir -p deps/build
    @[ -f deps/build/$(FFMPEG_TARBALL) ] || curl -fSL -o deps/build/$(FFMPEG_TARBALL) "$(FFMPEG_URL)"
    @tar -xf deps/build/$(FFMPEG_TARBALL) -C deps/build
    @rm -f deps/build/$(FFMPEG_TARBALL)

.PHONY: ffmpeg
ffmpeg: $(FFMPEG_OUT)/bin/ffmpeg
