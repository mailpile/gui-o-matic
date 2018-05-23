import copy
import importlib

# Note: This is NOT dict, because order matters.
#       Some GUIs are better than others, and we want to try them first.
#
_registry = (
    ('winapi',  'winapi'),
    ('macosx',  'macosx'),
    ('unity',   'unity'),
    ('gtk',     'gtkbase'),
)


def _known_guis():
    '''
    List known guis.
    '''
    return [gui for gui, lib in _registry]


def _gui_libname(gui):
    '''
    Convert a gui-name to a libname, assume well-formed if not in registry
    '''
    try:
        return 'gui_o_matic.gui.{}'.format(dict(_registry)[gui])
    except KeyError:
        return gui


def AutoGUI(config, *args, **kwargs):
    """
    Load and instanciate the best GUI available for this machine.
    """
    for candidate in config.get('_prefer_gui', _known_guis()):
        try:
            impl = importlib.import_module(_gui_libname(candidate))
            return impl.GUI( config, *args, **kwargs )
        except ImportError:
            pass

    raise NotImplementedError("No working GUI found!")

