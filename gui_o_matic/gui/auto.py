import copy
import importlib

# Note--only dict because of gtk gui
#
_registry = {
    'winapi':   'winapi',
    'macosx':   'macosx',
    'gtk':      'gtkbase', # The only non-identity mapping...
    'unity':    'unity',
}


def known_guis():
    '''
    List known guis.
    '''
    return _registry.keys()

def gui_libname( gui ):
    '''
    Convert a gui-name to a libname, assume well-formed if not in registry
    '''
    try:
        return 'gui_o_matic.gui.{}'.format( _registry[ gui ] )
    except KeyError:
        return gui


def AutoGUI(config, *args, **kwargs):
    """
    Load and instanciate the best GUI available for this machine.
    """
    for candidate in config.get( '_prefer_gui', known_guis() ):
        try:
            impl = importlib.import_module( gui_libname( candidate ) )
            return impl.GUI( config, *args, **kwargs )
        except ImportError:
            pass

    raise NotImplementedError("No working GUI found!")

