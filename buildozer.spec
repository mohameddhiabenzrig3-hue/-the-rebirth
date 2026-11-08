[app]
title = THE REBIRTH
package.name = therebirth
package.domain = com.therebirth
source.dir = .
source.include_exts = py,json,png,jpg,kv,atlas,txt
version = 1.0.0
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0
android.permissions = VIBRATE
android.api = 35
android.minapi = 23
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True
android.backup_rules =
android.debug_artifact = apk
p4a.branch = develop
p4a.bootstrap = sdl2
[buildozer]
log_level = 2
warn_on_root = 1
