#!/bin/bash
export PARPID=$$

export BASEDIR=$(cd $(dirname "$(readlink -f "$0" || echo "$0")"); pwd)
export ICON="$BASEDIR/icons/x11-flipper.png"
export NOTIFY="notify-send -i '$ICON'"

export ENABLE_DEVICES="xinput --list |perl -npe 's/^.*id=(\\\\d+).*\$/\$1/' |xargs -L 1 -I DEV xinput set-int-prop DEV 'Device Enabled' 8 1"
export DISABLE_NONTOUCH="xinput --list |grep -i -v -e master -e Touchscreen -e Power -e hotkeys |perl -npe 's/^.*id=(\\\\d+).*\$/\$1/' |xargs -L 1 -I DEV xinput set-int-prop DEV 'Device Enabled' 8 0"
export DISABLE_TOUCH="xinput --list |grep -i -v master |grep -e Touchscreen |perl -npe 's/^.*id=(\\\\d+).*\$/\$1/' |xargs -L 1 -I DEV xinput set-int-prop DEV 'Device Enabled' 8 0"

(
    cat <<tac
    {
        "app_name": "X11 Flipper",
        "indicator_icons": {
            "startup": "$ICON"
        },
        "indicator_menu": [
            {
                "label": "Laptop",
                "item": "laptop",
                "op": "shell",
                "args": ["xrandr -o normal",
                         "$ENABLE_DEVICES", "$DISABLE_TOUCH || true",
                         "$NOTIFY 'Laptop mode; disabled touchscreen'"],
                "sensitive": true
            },{
                "label": "Tablet",
                "item": "tablet",
                "op": "shell",
                "args": ["xrandr -o left",
                         "$ENABLE_DEVICES", "$DISABLE_NONTOUCH || true",
                         "$NOTIFY 'Tablet mode; touchscreen only'"],
                "sensitive": true
            },{
                "label": "Tent",
                "item": "tablet",
                "op": "shell",
                "args": ["xrandr -o inverted",
                         "$ENABLE_DEVICES", "$DISABLE_NONTOUCH || true",
                         "$NOTIFY 'Tent mode; touchscreen only'"],
                "sensitive": true
            },{
                "label": "Video",
                "item": "tv",
                "op": "shell",
                "args": ["xrandr -o normal",
                         "$ENABLE_DEVICES", "$DISABLE_NONTOUCH || true",
                         "$NOTIFY 'Video mode; touchscreen only'"],
                "sensitive": true
            },{
                "label": "Everything",
                "item": "tv",
                "op": "shell",
                "args": ["xrandr -o normal", "$ENABLE_DEVICES",
                         "$NOTIFY 'All input devices enabled'"],
                "sensitive": true
            }
        ]
    }
    OK GO
tac
) | (
    cd "$BASEDIR/.."
    python -m gui_o_matic
    kill $PARPID
)
