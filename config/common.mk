# Enable overlays
DEVICE_PACKAGE_OVERLAYS += \
	vendor/sora/overlays
# Load prebuilts
ifdef OCTO_PACKAGES
PRODUCT_PACKAGES += $(OCTO_PACKAGES)
endif
PRODUCT_ENFORCE_ARTIFACT_PATH_REQUIREMENTS := false
$(call inherit-product, vendor/sora/nikgapps/gapps/common.mk)