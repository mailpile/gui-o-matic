import copy

def AutoGUI(config, *args, **kwargs):
    """
    Load and instanciate the best GUI available for this machine.
    """

    required = config.get('require_gui')
    preferred = [pref.strip().lower() for pref in
                 (required or config.get('prefer_gui', '')).split()
                 if pref]

    if not preferred or 'macosx' in preferred:
        try:
            from gui_o_matic.gui.macosx import GUI
            return GUI(config, *args, **kwargs)
        except ImportError:
            pass

    if not preferred or 'unity' in preferred:
        try:
            from gui_o_matic.gui.unity import GUI
            return GUI(config, *args, **kwargs)
        except ImportError:
            pass

    if preferred and not required:
        config = copy.copy(config)
        for kw in ('prefer_gui', 'require_gui'):
            if kw in config:
                del config[kw]
        return AutoGUI(config, *args, **kwargs)

    raise NotImplementedError("No working GUI found!")
