
# Windows-specific includes, uses pywin32 for winapi
#
import win32api
import win32con
import win32gui
import win32gui_struct

# Utility imports
#
import re
import traceback

from gui_o_matic.gui.base import BaseGUI

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
    class Action( object ):
        '''
        Class binding a string id to numeric id, op, and action
        '''

        _base_gui_id = 1024

        _actions = {}

        @classmethod
        def register( cls, action ):
            action._gui_id = cls._base_gui_id
            cls._actions[ action._gui_id ] = action
            cls._base_gui_id += 1

        @classmethod
        def byId( cls, gui_id ):
            return cls._actions[ gui_id ]

        def __init__( self, gui, identifier, label, operation, sensitive, args ):
            self.gui = gui
            self.identifier = identifier,
            self.label = label
            self.operation = operation
            self.sensitive = sensitive
            self.args = args
            self.register( self )

        def get_id( self ):
            return self._gui_id

        def __call__( self ):
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

        _next_window_class_id = 0

        @classmethod
        def _make_window_class_name( cls ):
            result = "window_class_{}".format( cls._next_window_class_id )
            cls._next_window_class_id += 1
            return result

        def __init__(self, title, width, height, style ):
            '''Setup a window class and a create window'''
            self.module_handle = win32gui.GetModuleHandle(None)

            # Setup window class
            #
            self.window_class_name = self._make_window_class_name()
            self.message_map = {
                win32con.WM_PAINT: self._on_paint,
                win32con.WM_CLOSE: self._on_close,
                win32con.WM_COMMAND: self._on_command,
                }

            self.window_class = win32gui.WNDCLASS()
            self.window_class.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
            self.window_class.lpfnWndProc = self.message_map
            self.window_class.hInstance = self.module_handle
            self.window_class.hCursor = win32gui.LoadCursor( None, win32con.IDC_ARROW )
            self.window_class.hbrBackground = win32con.COLOR_WINDOW
            self.window_class.lpszClassName = self.window_class_name
            
            self.window_classHandle = win32gui.RegisterClass( self.window_class )
            assert( self.window_classHandle )

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
            
        def _on_command( self, window_handle, message, wparam, lparam ):
            return 0

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

        def close( self ):
            self.onClose()


    _variable_re = re.compile( "%\(([\w]+)\)" )

    def _lookup_token( match ):
        '''
        Convert re match token to variable definitions.
        '''
        return self.variables[ match.group( 1 ) ]

    def _resolve_variables( self, path ):
        '''
        Apply %(variable) expansion.
        '''
        return _variable_re.sub( self._gtk_lookup_token, path )

    def __init__(self, config, variables = {'icon_theme': 'light' } ):
        '''
        Inflate superclass--defer construction to run().
        '''
        super(WinapiGUI,self).__init__(config)
        self.variables = variables
        self.ready = False
        
    def run( self ):
        '''
        Initialize GUI and enter run loop
        '''
        win32gui.InitCommonControls()

        # Stub code!
        self.main_window = self.Window(title = self.config['app_name'],
                                       width = self.config['main_window']['width'],
                                       height = self.config['main_window']['height'],
                                       style = self.Window.main_window_style)

        self.main_window.set_visibility( self.config['main_window']['show'] )

        self.splash_screen = self.Window(title = self.config['app_name'],
                                       width = self.config['main_window']['width'],
                                       height = self.config['main_window']['height'],
                                       style = self.Window.splash_screen_style)        
        # Enter run loop
        #
        self.ready = True
        try:
            win32gui.PumpMessages()
        finally:
            win32gui.PostQuitMessage(0)
        
    def terminal(self, command='/bin/bash', title=None, icon=None):
        print( "FIXME: Terminal not supported!" )

    def _add_menu_item(self, item='item', label='Menu item', sensitive=False,
                             op=None, args=None, **ignored_kwargs):
        pass

    def set_status(self, status='startup'):
        print('STATUS: %s' % status)

    def quit(self):
        win32gui.PostQuitMessage(0)     
        raise KeyboardInterrupt("User quit")

    def set_item_label(self, item=None, label=None):
        pass

    def set_item_sensitive(self, item=None, sensitive=True):
        pass

    def set_substatus(self,
            substatus=None, label=None, hint=None, icon=None, color=None):
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
