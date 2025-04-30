set -eu
if [[ ! -f "vendor/sora/.venv/bin/python3" ]]
then
    echo "Creating venv..."
    python3 -m venv vendor/sora/.venv
fi
vendor/sora/.venv/bin/pip install -r $PWD/vendor/sora/requirements.txt
export PREBUILTS=$(vendor/sora/.venv/bin/python3 -m vendor.sora.tools.prebuilts $PWD/vendor/sora/Prebuilts.yml)
export OCTO_PACKAGES="$PREBUILTS"
echo "Prebuilt packages: $OCTO_PACKAGES"
set +eu