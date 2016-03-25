def AutoIndicator(*args, **kwargs):
    """
    Load and instanciate the best indicator available for this machine.
    """

    try:
        from macosx import Indicator
        return Indicator(*args, **kwargs)
    except ImportError:
        pass

    try:
        from unity import Indicator
        return Indicator(*args, **kwargs)
    except ImportError:
        pass

    raise NotImplementedError("No working Indicator found!")
