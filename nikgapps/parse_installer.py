import os
import re
import shutil
import zipfile

TEMPLATE_APK = """
// {filename}
android_app_import {
	name: "{svc_name}",
	owner: "gapps",
	apk: "{apk}",
	preprocessed: true,
	presigned: true,
	dex_preopt: {
		enabled: false,
	},
	product_specific: {product},
    privileged: {priveleged},
    overrides: {overrides},
    system_ext_specific: {system_ext},
}
"""

LIBRARY_MULTI = """
// {filename}
cc_prebuilt_library_shared {
	name: "{svc_name}",
	owner: "gapps",
	strip: {
		none: true,
	},
	target: {
		android_arm64: {
			srcs: ["64/{file}"],
			shared_libs: ["libc", "libm", "libc++", "libdl" ],
		},
        android_arm: {
			srcs: ["32/{file}"],
			shared_libs: ["libc", "libm", "libc++", "libdl" ],
		},
	},
	compile_multilib: "both",
	prefer: true,
	product_specific: {product},
    system_ext_specific: {system_ext},
    check_elf_files: false
}
"""

LIBRARY_64 = """
// {filename}
cc_prebuilt_library_shared {
	name: "{svc_name}",
	owner: "gapps",
	strip: {
		none: true,
	},
	target: {
		android_arm64: {
			srcs: ["64/{file}"],
			shared_libs: ["libc", "libm", "libc++", "libdl" ],
		},
	},
	compile_multilib: "both",
	prefer: true,
	product_specific: {product},
    system_ext_specific: {system_ext},
    check_elf_files: false
}
"""
LIBRARY_32 = """
// {filename}
cc_prebuilt_library_shared {
	name: "{svc_name}",
	owner: "gapps",
	strip: {
		none: true,
	},
	target: {
        android_arm: {
			srcs: ["32/{file}"],
			shared_libs: ["libc", "libm", "libc++", "libdl" ],
		},
	},
	compile_multilib: "both",
	prefer: true,
	product_specific: {product},
    system_ext_specific: {system_ext},
    check_elf_files: false
}
"""

JAR = """
dex_import {
	name: "{svc_name}",
	owner: "gapps",
	jars: ["{svc_name}.jar"],
	product_specific: {product},
    system_ext_specific: {system_ext},
}

"""

def create_multiline_re(name):
    return "^" + name + r"=\"\s*([^\"]*?)\s*\""


def create_singleline_re(name):
    return "^" + name + r"=\"(.*)\""


files_re = create_multiline_re("file_list")
aosp_apps_to_rm = create_multiline_re("remove_aosp_apps_from_rom")
part_re = create_singleline_re("default_partition")
if os.path.exists("gapps"):
    shutil.rmtree("gapps")
os.makedirs("gapps")
common = open("gapps/common.mk", "w")
common.write("PRODUCT_SOONG_NAMESPACES += vendor/sora/nikgapps/gapps\n")


def parse_package(item_zip: zipfile.ZipFile, name: str):
    install_sh = item_zip.open("installer.sh").read().decode()
    file_list = re.search(files_re, install_sh, re.MULTILINE).group(1).split("\n")
    partition = re.search(part_re, install_sh, re.MULTILINE).group(1)
    is_product = partition == "product"
    is_system_ext = partition == "system_ext"
    print(partition)
    overrides = (
        re.search(aosp_apps_to_rm, install_sh, re.MULTILINE).group(1).split("\n")
    )
    libs = {}
    for file in file_list:
        if file.endswith(".apk"):
            svc_name = file.split("/")[-1].split(".")[0]
            blueprint = TEMPLATE_APK.replace("{svc_name}", svc_name)
            blueprint = blueprint.replace("{apk}", file.split("/")[-1])
            blueprint = blueprint.replace(
                "{priveleged}", str("priv-app" in file).lower()
            )
            blueprint = blueprint.replace("{overrides}", str(overrides).replace("'", '"'))
            blueprint = blueprint.replace("{product}", str(is_product).lower())
            blueprint = blueprint.replace("{system_ext}", str(is_system_ext).lower())
            blueprint = blueprint.replace("{filename}", name)
            os.makedirs("gapps/" + svc_name, exist_ok=True)
            with open("gapps/" + svc_name + "/Android.bp", "w") as f:
                f.write(blueprint)
            source = item_zip.open(file)
            target = open("gapps/" + svc_name + "/" + file.split("/")[-1], "wb")
            with source, target:
                shutil.copyfileobj(source, target)
            common.write("\nPRODUCT_PACKAGES += " + svc_name + "\n")
        elif file.endswith(".xml") or file.endswith(".der"):
            permname = file.split("/")[-1]
            source = item_zip.open(file)
            os.makedirs("gapps/xmls", exist_ok=True)
            target = open("gapps/xmls/" + permname, "wb")
            with source, target:
                shutil.copyfileobj(source, target)
            common.write(
                "\nPRODUCT_COPY_FILES += vendor/sora/nikgapps/gapps/xmls/"
                + permname
                + ":$(TARGET_COPY_OUT_"
                + partition.upper()
                + ")"
                + file.replace("___", "/")
            )
        elif file.endswith(".so"):
            lib = file.split("/")[-1]
            if lib not in libs:
                libs[lib] = {"product": partition == "product", "files": []}
            libs[lib]["files"].append(file)
        elif file.endswith(".jar"):
            filename = file.split("/")[-1]
            svc_name = filename.replace(".jar", "")
            blueprint = JAR.replace("{svc_name}", svc_name)
            blueprint = blueprint.replace("{product}", str(is_product).lower())
            blueprint = blueprint.replace("{system_ext}", str(is_system_ext).lower())
            os.makedirs(f"gapps/jars/{svc_name}", exist_ok=True)
            with open(f"gapps/jars/{svc_name}/Android.bp", "w") as f:
                f.write(blueprint)
            source = item_zip.open(file)
            target = open(f"gapps/jars/{svc_name}/{svc_name}.jar", "wb")
            with source, target:
                shutil.copyfileobj(source, target)
            common.write("\nPRODUCT_PACKAGES += " + svc_name + "\n")
        else:
            print("Unknown file type:", file.split(".")[-1], "at", file)
    for lib, libdesc in libs.items():
        os.makedirs("gapps/libs/" + lib + "/64")
        os.makedirs("gapps/libs/" + lib + "/32")
        files = libdesc["files"]
        for file in files:
            filename = file.split("/")[-1]
            print(file, "64" in file)
            if "64" in file:
                filepath = f"gapps/libs/{lib}/64/{filename}"
            else:
                filepath = f"gapps/libs/{lib}/32/{filename}"
            source = item_zip.open(file)
            target = open(filepath, 'wb')
            with source, target:
                shutil.copyfileobj(source, target)
        if len(files) > 1:
            template = LIBRARY_MULTI
        elif "lib64" in files[0]:
            template = LIBRARY_64
        else:
            template = LIBRARY_32
        svc_name = lib.replace(".so", "")
        blueprint = template.replace("{file}", lib)
        blueprint = blueprint.replace("{svc_name}", svc_name)
        blueprint = blueprint.replace("{filename}", name)
        blueprint = blueprint.replace("{product}", str(libdesc["product"]).lower())
        blueprint = blueprint.replace("{system_ext}", str(is_system_ext).lower())
        with open("gapps/libs/" + lib + "/Android.bp", "w") as f:
            f.write(blueprint)
        common.write(f"\nPRODUCT_PACKAGES += {svc_name}\n")

def parse_nikgapps(nikgapps_zip: zipfile.ZipFile):
    for file in nikgapps_zip.filelist:
        if file.filename.startswith("AppSet"):
            parse_package(zipfile.ZipFile(nikgapps_zip.open(file.filename)), file.filename)


if __name__ == "__main__":
    # parse_package(zipfile.ZipFile("CarrierServices.zip", "r"))
    parse_nikgapps(zipfile.ZipFile("nikgapps.zip"))
