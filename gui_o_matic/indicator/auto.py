def AutoIndicator(*args, **kwargs):
    """
    Load and instanciate the best indicator available for this machine.
    """

    try:
        from gui_o_matic.indicator.macosx import Indicator
        return Indicator(*args, **kwargs)
    except ImportError:
        pass

    try:
        from gui_o_matic.indicator.unity import Indicator
        return Indicator(*args, **kwargs)
    except ImportError:
        pass

    raise NotImplementedError("No working Indicator found!")
