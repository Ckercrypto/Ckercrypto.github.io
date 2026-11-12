[app]

# (str) Title of your application
title = Trans Plate Designer

# (str) Package name / domain  ->  org.transreza.platedesigner
package.name = platedesigner
package.domain = org.transreza

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (fonts, icons, json ...)
source.include_exts = py,png,jpg,ttf,json,txt,ico
source.include_patterns = assets/*,assets/fonts/*,assets/icons/*

# (list) Directories / patterns to exclude from the APK
source.exclude_dirs = tests, bin, ci, tools, build, dist, .buildozer, __pycache__, .github, screenshots
source.exclude_patterns = *.spec,README.md

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# python-bidi must stay < 0.5 (0.5+ is a Rust extension that p4a cannot build); it needs six.
requirements = python3,kivy==2.3.0,pillow,arabic-reshaper,python-bidi==0.4.2,six,androidstorage4kivy,pyjnius

# (str) Presplash / icon
presplash.filename = %(source.dir)s/assets/presplash.png
icon.filename = %(source.dir)s/assets/icon.png
android.presplash_color = #FFFFFF

# (list) Supported orientations (portrait and landscape)
orientation = portrait, landscape, portrait-reverse, landscape-reverse

# (bool) Fullscreen
fullscreen = 0

# Exports are written to MediaStore (Documents / Pictures) through
# androidstorage4kivy; that needs no permission on Android 10+.  Old devices
# (API <= 28) need WRITE_EXTERNAL_STORAGE.
android.permissions = (name=android.permission.WRITE_EXTERNAL_STORAGE;maxSdkVersion=28), (name=android.permission.READ_EXTERNAL_STORAGE;maxSdkVersion=32)

# (int) Target / minimum API, NDK
android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24

# (bool) Automatically accept SDK license agreements (needed on CI)
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature
android.allow_backup = True

# (str) python-for-android release (pinned for reproducible builds)
p4a.branch = v2024.01.21

# (str) Bootstrap
p4a.bootstrap = sdl2


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 0
