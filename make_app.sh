#!/bin/bash
#
# Automated build script for Instagiffer app and dmg installer
#

# Determine verison dynamically
export INSTAGIFFER_VERSION=`cat instagiffer.py | perl -ne 'if(/INSTAGIFFER_VERSION=.([0-9\.]+)/){print "$1\n"}'`
export INSTAGIFFER_PRERELEASE=`cat instagiffer.py | perl -ne 'if(/INSTAGIFFER_PRERELEASE=.([0-9\.]+)/){print "$1\n"}'`

APP_PATH=dist/Instagiffer.app

function remove_arch () {
    lipo -output build/lipo.tmp -remove "$1" "$2" && mv build/lipo.tmp "$2"
}

function make_clean(){
	rm -Rf ~/Library/Application\ Support/Instagiffer
	>instagiffer-event.log
	rm -Rf dist/ build/ *.pyc *.dmg *.pkg
	rm -Rf ~/.cache/fontconfig macdeps/im/var
	echo "Cleaned Instagiffer artifacts"
}


function optimize_binaries(){
	for i in ${APP_PATH}/Contents/Resources/lib/python2.7/lib-dynload/* ; do
		remove_arch ppc ${i}
    		remove_arch i386 ${i}
	done
}


function make_app(){
	python -m compileall instagiffer.py 
	echo "Building Mac release with Py2App"
	if ! python setup-mac-py2app.py py2app ; then
		echo "Error building app with py2app"
		exit 1
	fi

	#optimize_binaries
}


function make_pkg(){
	productbuild --component $APP_PATH /Applications Instagiffer-${INSTAGIFFER_VERSION}${INSTAGIFFER_PRERELEASE}.pkg
}

function make_dmg(){
	echo "Building DMG Installer"
	img_name=Instagiffer-${INSTAGIFFER_VERSION}${INSTAGIFFER_PRERELEASE}
	src_img=${img_name}.sparseimage
	dst_img=${img_name}.dmg

	rm -f $src_img $dst_img

	# Make a copy of the sparseimage template
	cp Instagiffer.sparseimage $src_img
	hdiutil attach $src_img

	# Copy in the app
	cp -a $APP_PATH /Volumes/Instagiffer/

	# Wait...
	echo "Manually place the instagiffer icon in the correct position"
	for x in `seq 10 1`; do
		echo $x
		sleep 1
	done

	# Detach
	hdiutil detach /dev/disk1s2	

	# Convert to a DMG
	hdiutil convert $src_img -format UDZO -o $dst_img -imagekey zlib-level=9

	# Set the icon
	python -c "import Cocoa;import sys;Cocoa.NSWorkspace.sharedWorkspace().setIcon_forFile_options_(Cocoa.NSImage.alloc().initWithContentsOfFile_(sys.argv[1].decode('utf-8')), sys.argv[2].decode('utf-8'), 0) or sys.exit('Failed')" \
	 instagiffer.icns $dst_img

	# delete sparseimg
	rm $src_img
}

function make_test(){
	open -a $APP_PATH
}

#
#
# Main
#
#

if [ x"$1" = x"clean" ] ; then
	make_clean
else
	make_clean
	make_app
	#make_test
	make_dmg
	make_pkg
fi

exit 0
