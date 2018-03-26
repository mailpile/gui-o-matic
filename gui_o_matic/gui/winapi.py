
# Windows-specific includes, uses pywin32 for winapi
#
import win32api
import win32con
import win32gui
import win32gui_struct
import ctypes

# Utility imports
#
import re
import tempfile
import PIL.Image
import os
import uuid
import traceback
import atexit
import itertools

from gui_o_matic.gui.base import BaseGUI



class Image( object ):
    '''
    Helper class for importing arbitrary graphics to winapi bitmaps. Mode is a
    tuple of (winapi image type, file extension, and cleanup callback).
    '''

    @classmethod
    def Bitmap( cls, path, size = None ):
        return cls( path, size, mode = (win32con.IMAGE_BMP,'bmp',win32gui.DeleteObject))

    # https://blog.barthe.ph/2009/07/17/wmseticon/
    #
    @classmethod
    def Icon( cls, path, size ):
        return cls( path, mode = (win32con.IMAGE_ICON,'ico',win32gui.DestroyIcon), size = size )

    @classmethod
    def IconLarge( cls, path ):
        dims =(win32con.SM_CXICON, win32con.SM_CYICON)
        size = tuple(map(win32api.GetSystemMetrics,dims))
        return cls.Icon( path, size )

    @classmethod
    def IconSmall( cls, path ):
        dims =(win32con.SM_CXSMICON, win32con.SM_CYSMICON)
        size = tuple(map(win32api.GetSystemMetrics,dims))
        return cls.Icon( path, size )

    def __init__( self, path, mode, size = None ):
        source = PIL.Image.open( path )
        if source.mode != 'RGBA':
            source = source.convert( 'RGBA' )
        if size:
            factor = float(max( size )) / max( source.size )
            new_size = tuple([ int(factor * dim) for dim in source.size ])
            source = source.resize( new_size, PIL.Image.LANCZOS )
            source.thumbnail( size, PIL.Image.ANTIALIAS )

        self.size = source.size
        self.mode = mode
            
        with tempfile.NamedTemporaryFile( delete = False ) as handle:
            filename = handle.name
            source.save( handle, mode[ 1 ] )

        try:
            self.handle = win32gui.LoadImage( None,
                                              handle.name,
                                              mode[ 0 ],
                                              source.width,
                                              source.height,
                                              win32con.LR_LOADFROMFILE )
        finally:
            os.unlink( filename )

    def __del__( self ):
        # TODO: swap mode to a more descriptive structure
        #
        #self.mode[2]( self.handle )
        pass



class Action( object ):
    '''
    Class binding a string id to numeric id, op, and action, allowing
    WM_COMMAND etc to be easily mapped to gui-o-matic protocol elements.
    '''

    # Generate ids per action--Windows recommends we avoid low IDs
    #
    _base_gui_id = 1024

    # Registry of actions, by id
    #
    _actions = {}

    @classmethod
    def register( cls, action ):
        '''
        Generate and associate an id with the given action
        '''
        action._gui_id = cls._base_gui_id
        cls._actions[ action._gui_id ] = action
        cls._base_gui_id += 1
            
    @classmethod
    def byId( cls, gui_id ):
        '''
        Get a registered action by id, probably for invoking it.
        '''
        return cls._actions[ gui_id ]

    def __init__( self, gui, identifier, label, operation = None, sensitive = False, args = None ):
        '''
        Bind the action state to the gui for later invocation or modification.
        '''
        self.gui = gui
        self.identifier = identifier
        self.label = label
        self.operation = operation
        self.sensitive = sensitive
        self.args = args
        self.register( self )

    def get_id( self ):
        return self._gui_id

    def __call__( self ):
        '''
        Apply the bound action arguments
        '''
        assert( self.sensitive )
        self.gui._do( op = self.operation, args = self.args )


class Window( object ):
    '''
    Window class stub
    '''
    # Standard window style except disable resizing
    #
    main_window_style = win32con.WS_OVERLAPPEDWINDOW \
                        ^ win32con.WS_THICKFRAME     \
                        ^ win32con.WS_MAXIMIZEBOX

    # Window style with no frills
    #
    splash_screen_style = win32con.WS_POPUP

    # Window styel for systray
    #
    systray_style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
    
    _next_window_class_id = 0

    @classmethod
    def _make_window_class_name( cls ):
        result = "window_class_{}".format( cls._next_window_class_id )
        cls._next_window_class_id += 1
        return result

    _notify_event_id = win32con.WM_USER + 22

    def __init__(self, title, style,
                 width = win32con.CW_USEDEFAULT,
                 height = win32con.CW_USEDEFAULT,
                 messages = {}):
        '''Setup a window class and a create window'''
        self.module_handle = win32gui.GetModuleHandle(None)
        self.systray = False
        
        # Setup window class
        #
        self.window_class_name = self._make_window_class_name()
        self.message_map = {
             win32con.WM_PAINT: self._on_paint,
             win32con.WM_CLOSE: self._on_close,
             win32con.WM_COMMAND: self._on_command,
             self._notify_event_id: self._on_notify,
             }
        self.message_map.update( messages )

        self.window_class = win32gui.WNDCLASS()
        self.window_class.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.window_class.lpfnWndProc = self.message_map
        self.window_class.hInstance = self.module_handle
        self.window_class.hCursor = win32gui.LoadCursor( None, win32con.IDC_ARROW )
        self.window_class.hbrBackground = win32con.COLOR_WINDOW
        self.window_class.lpszClassName = self.window_class_name
            
        self.window_classHandle = win32gui.RegisterClass( self.window_class )

        self.window_handle = win32gui.CreateWindow(
            self.window_class_name,
            title,
            style,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            width,
            height,
            None,
            None,
            self.module_handle,
            None )
        
    def set_visibility( self, visibility  ):
        state = win32con.SW_SHOW if visibility else win32con.SW_HIDE
        win32gui.ShowWindow( self.window_handle, state )
        win32gui.UpdateWindow( self.window_handle )

    def set_icon( self, small_icon, big_icon ):
        # https://stackoverflow.com/questions/16472538/changing-taskbar-icon-programatically-win32-c
        #
        win32gui.SendMessage(self.window_handle,
                             win32con.WM_SETICON,
                             win32con.ICON_BIG,
                             big_icon.handle )
        
        win32gui.SendMessage(self.window_handle,
                             win32con.WM_SETICON,
                             win32con.ICON_SMALL,
                             small_icon.handle )

    def set_systray( self, small_icon = None, text = '' ):
        if small_icon:
            message = win32gui.NIM_MODIFY if self.systray else win32gui.NIM_ADD
            data = (self.window_handle,
                          0,
                          win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                          self._notify_event_id,
                          small_icon.handle,
                          text)
        elif self.systray:
            message = win32gui.NIM_DELETE
            data = (self.window_handle, 0)
        else:
            message = None
            data = tuple()

        lookup = {
            win32gui.NIM_MODIFY: "modify",
            win32gui.NIM_ADD: "add",
            win32gui.NIM_DELETE: "delete",
            None: 'no-op'
        }
        print( "{}: {}".format( lookup[ message ], data ) )

        self.systray = True if small_icon else False

        if message is not None:
            win32gui.Shell_NotifyIcon( message, data )

    def set_menu( self, actions ):
        self.menu_actions = actions

    def _on_command( self, window_handle, message, wparam, lparam ):
        action_id = win32gui.LOWORD(wparam)
        print( "command {}".format( action_id ) )
        action = Action.byId( action_id )
        action()
        return 0

    def _on_notify( self, window_handle, message, wparam, lparam  ):
        if lparam == win32con.WM_RBUTTONDOWN:
            self._show_menu()
        return True

    def _show_menu( self ):
        menu = win32gui.CreatePopupMenu()
        for action in self.menu_actions:
            flags = win32con.MF_STRING
            if not action.sensitive:
                flags |= win32con.MF_GRAYED
            win32gui.AppendMenu( menu, flags, action.get_id(), action.label )
        
        pos = win32gui.GetCursorPos()
        
        win32gui.SetForegroundWindow( self.window_handle )
        win32gui.TrackPopupMenu( menu,
                                 win32con.TPM_LEFTALIGN | win32con.TPM_BOTTOMALIGN,
                                 pos[ 0 ],
                                 pos[ 1 ],
                                 0,
                                 self.window_handle,
                                 None )
        win32gui.PostMessage( self.window_handle, win32con.WM_NULL, 0, 0 )

    def _on_paint( self, window_handle, message, wparam, lparam ):
        (hdc, paintStruct) = win32gui.BeginPaint( self.window_handle )
        #print paintStruct
        #win32gui.FillRect( hdc, paintStruct[2], win32con.COLOR_WINDOW )
        message = "text message"
        win32gui.DrawText( hdc, message, len( message ), (5,5,100,100), win32con.DT_SINGLELINE | win32con.DT_NOCLIP  )
        win32gui.EndPaint( self.window_handle, paintStruct )
        #win32gui.DrawMenuBar( self.window_handle )
        return 0

    def _on_close( self, window_handle, message, wparam, lparam ):
        self.set_visibility( False )
        return 0

    def __del__( self ):
        self.set_systray( None, None )
        win32gui.DestroyWindow( self.window_handle )
        win32gui.UnregisterClass( self.window_class_name, self.window_class )

    def close( self ):
        self.onClose()

class WinapiGUI(BaseGUI):
    """
    Winapi GUI, using pywin32 to programatically generate/update GUI components.

    Background: pywin32 presents the windows C API via python bindings, with
    minimal helpers where neccissary. In essence, using pywin32 is C winapi
    programming, just via python, a very low-level experience. Some things are
    slightly different from C(perhaps to work with the FFI), some things plain
    just don't work(unclear if windows or python is at fault), some things are
    entirely abscent(for example, PutText(...)). In short, it's the usual
    windows/microsoft experience. When in doubt, google C(++) examples and msdn
    articles.

    Structure: We create and maintain context for two windows, applying state
    changes directly to the associated context. While a declarative approach
    would be possible, it would run contrary to WINAPI's design and hit some
    pywin32 limitations. For asthetic conformance, each window will have it's
    own window class and associated resources. We will provide a high level
    convience wrapper around window primatives to abstract much of the c API
    boilerplate.

    For indicator purposes, we create a system tray resource. This also requires
    a window, though the window is never shown. The indicator menu is attached
    to the systray, as are the icons.

    TODO: Notifications
    
    Window Characteristics:
      - Style: Splash vs regular window. This maps pretty well onto window
        class style in winapi. Splash is an image with progress bar and text,
        regular window has regular boarders and some status items.
      - Graphic resources: For winapi, we'll have to convert all graphics into
        bitmaps, using winapi buffers to hold the contents.
      - Menu items: (regular window only) We'll have to manage associations
        between menu items, actions, and all that: For an item ID (gui-o-matic
        protocol), we'll have to track menu position, generate a winapi command
        id, and catch/map associated WM_COMMAND event back to actions. This
        allows us to toggle sensitivity, replace text, etc.
    """

    _variable_re = re.compile( "%\(([\w]+)\)s" )

    def _lookup_token( self, match ):
        '''
        Convert re match token to variable definitions.
        '''
        return self.variables[ match.group( 1 ) ]

    def _resolve_variables( self, path ):
        '''
        Apply %(variable) expansion.
        '''
        return self._variable_re.sub( self._lookup_token, path )

    def __init__(self, config, variables = {'theme': 'light' } ):
        '''
        Inflate superclass--defer construction to run().
        '''
        super(WinapiGUI,self).__init__(config)
        self.variables = variables
        self.ready = False
        self.statuses = {}
        self.items = {}

    def run( self ):
        '''
        Initialize GUI and enter run loop
        '''
        # https://stackoverflow.com/questions/1551605/how-to-set-applications-taskbar-icon-in-windows-7/1552105#1552105
        #
        self.appid = unicode( uuid.uuid4() )
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.appid)
        win32gui.InitCommonControls()

        items = itertools.chain( self.config['indicator']['menu'],
                                 self.config['main_window']['actions'] )
        for item in items:
            action = Action( self,
                             identifier = item['item'],
                             label = item['label'],
                             operation = item.get('op'),
                             args = item.get('args'),
                             sensitive = item.get('sensitive', False))
            self.items[action.identifier] = action

        self.systray_window = Window(title = self.config['app_name'],
                                     style = Window.systray_style)

        menu_items = [ self.items[ item['item'] ] for item in self.config['indicator']['menu'] ]
        self.systray_window.set_menu( menu_items )
        
        self.main_window = Window(title = self.config['app_name'],
                                  style = Window.main_window_style,
                                  width = self.config['main_window']['width'],
                                  height = self.config['main_window']['height'])
        
        self.main_window.set_visibility( self.config['main_window']['show'] )
        
        self.splash_screen = Window(title = self.config['app_name'],
                                    style = Window.splash_screen_style,
                                    width = self.config['main_window']['width'],
                                    height = self.config['main_window']['height'])


        self.windows = [ self.main_window,
                         self.splash_screen,
                         self.systray_window ]

        self.set_status( 'normal' )

        #FIXME: Does not run!
        #
        @atexit.register
        def cleanup_context():
            print( "cleanup" )
            self.systray_window.set_systray( None, None )
            win32gui.PostQuitMessage(0)

        # Enter run loop
        #
        self.ready = True
        win32gui.PumpMessages()
        
    def terminal(self, command='/bin/bash', title=None, icon=None):
        print( "FIXME: Terminal not supported!" )

    def _add_menu_item(self, item='item', label='Menu item', sensitive=False,
                             op=None, args=None, **ignored_kwargs):
        pass

    def set_status(self, status='startup'):
        icon_path = self._resolve_variables( self.config['icons'][status] )
        small_icon = Image.IconSmall( icon_path )
        large_icon = Image.IconLarge( icon_path )

        for window in self.windows:
            window.set_icon( small_icon, large_icon )

        systray_hover_text = self.config['app_name'] + ": " + status
        self.systray_window.set_systray( small_icon, systray_hover_text )

        print('STATUS: %s' % status)

    def quit(self):
        win32gui.PostQuitMessage(0)     
        raise KeyboardInterrupt("User quit")

    def set_item_label(self, item=None, label=None):
        self.items[item].label = label

    def set_item_sensitive(self, item=None, sensitive=True):
        self.items[item].sensitive = sensitive
        
    def set_substatus(self, substatus=None, label=None, hint=None, icon=None, color=None):
        pass

    def update_splash_screen(self, message=None, progress=None):
        pass

    def set_next_error_message(self, message=None):
        self.next_error_message = message

    def show_splash_screen(self, height=None, width=None,
                           progress_bar=False, image=None,
                           message=None, message_x=0.5, message_y=0.5):
        self.splash_screen.set_visibility( True )
        print( "show splash" )

    def hide_splash_screen(self):
        self.splash_screen.set_visibility( False )

    def show_main_window(self):
        self.main_window.set_visibility( True )

    def hide_main_window(self):
        self.main_window.set_visibility( False )

    def _report_error(self, e):
        traceback.print_exc()
        self.notify_user(
                (self.next_error_message or 'Error: %(error)s')
                % {'error': unicode(e)})

    def notify_user(self, message='Hello', popup=False):
        print('NOTIFY: %s' % message)

GUI = WinapiGUI
