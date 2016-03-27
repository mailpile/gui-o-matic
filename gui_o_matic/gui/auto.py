def AutoGUI(*args, **kwargs):
    """
    Load and instanciate the best GUI available for this machine.
    """

    try:
        from gui_o_matic.gui.macosx import GUI
        return GUI(*args, **kwargs)
    except ImportError:
        pass

    try:
        from gui_o_matic.gui.unity import GUI
        return GUI(*args, **kwargs)
    except ImportError:
        pass

    raise NotImplementedError("No working GUI found!")
