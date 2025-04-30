# TARGET_DESKTOP_ROOTFS can be set in vendor makefiles to override the default
# desktop rootfs image for Maru. Note that the path must be relative to the
# AOSP workspace root directory, which can easily be done by prefixing the path
# with $(LOCAL_PATH).
TARGET_BOOTANIMATION := $(call my-dir)/bootanimation.zip
