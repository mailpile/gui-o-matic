
# Windows-specific includes, uses pywin32 for winapi
#
import win32api
import win32con
import win32gui
import win32gui_struct
import win32ui
import commctrl
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
import struct

import pil_bmp_fix

# Work-around till upstream PIL is patched.
#
BMP_FORMAT = "BMP+ALPHA"
PIL.Image.register_save( BMP_FORMAT, pil_bmp_fix._save )

from gui_o_matic.gui.base import BaseGUI

class Image( object ):
    '''
    Helper class for importing arbitrary graphics to winapi bitmaps. Mode is a
    tuple of (winapi image type, file extension, and cleanup callback).
    '''

    @classmethod
    def Bitmap( cls, *args, **kwargs ):
        mode = (win32con.IMAGE_BITMAP,'bmp',win32gui.DeleteObject)
        return cls( *args, mode = mode, **kwargs )

    # https://blog.barthe.ph/2009/07/17/wmseticon/
    #
    @classmethod
    def Icon( cls, *args, **kwargs ):
        mode = (win32con.IMAGE_ICON,'ico',win32gui.DestroyIcon)
        return cls( *args, mode = mode, **kwargs )

    @classmethod
    def IconLarge( cls, *args, **kwargs ):
        dims =(win32con.SM_CXICON, win32con.SM_CYICON)
        size = tuple(map(win32api.GetSystemMetrics,dims))
        return cls.Icon( *args, size = size, **kwargs )

    @classmethod
    def IconSmall( cls, *args, **kwargs ):
        dims =(win32con.SM_CXSMICON, win32con.SM_CYSMICON)
        size = tuple(map(win32api.GetSystemMetrics,dims))
        return cls.Icon( *args, size = size, **kwargs )

    @staticmethod
    def _winapi_bitmap( source ):
        '''
        try to create a bitmap in memory

        NOTE: Doesn't work! FillRect always paints with background!
        '''
        assert( source.mode == 'RGBA' )
        bitmap = win32gui.CreateBitmap( source.width,
                                      source.height,
                                      1,
                                      32,
                                      None )
        hdc = win32gui.GetDC( None )
        hdc_mem = win32gui.CreateCompatibleDC( hdc )
        prior = win32gui.SelectObject( hdc_mem, bitmap )

        pixels = source.load()

        '''
        for x in range( source.width ):
            for y in range( source.height ):
                pixel = struct.pack( '@BBBB', *pixels[ x, y ] )
                #pixel = struct.pack('@BBBB', 0, 0, 0, 0 )
                color = struct.unpack("@i", pixel )[ 0 ]
                print "{} {} {}".format( x, y, color )
                brush = win32gui.CreateSolidBrush( color )
                win32gui.FillRect( hdc_mem, ( x, y, 1, 1 ), brush )
        '''
        pixel = struct.pack('@BBBB', 0, 255, 255, 0  )
        brush = win32gui.CreateSolidBrush( struct.unpack( "@i", pixel )[ 0 ] )
        win32gui.FillRect( hdc_mem, ( 0, 0, source.width, source.height ), brush )

        print "done!"

        win32gui.SelectObject( hdc_mem, prior )
        win32gui.DeleteDC( hdc_mem )
        win32gui.ReleaseDC( None, hdc )
        
        return bitmap

    def __init__( self, path, mode, size = None, debug = None ):
        '''
        Load the image into memory, with appropriate conversions.

        size:
          None: use image size
          number: scale image size
          tuple: transform image size
        '''
        source = PIL.Image.open( path )
        if source.mode != 'RGBA':
            source = source.convert( 'RGBA' )
        if size:
            if not hasattr( size, '__len__' ):
                factor = float( size ) / max( source.size )
                size = tuple([ int(factor * dim) for dim in source.size ])
            source = source.resize( size, PIL.Image.ANTIALIAS )
            #source.thumbnail( size, PIL.Image.ANTIALIAS )

        self.size = source.size
        self.mode = mode

        if debug:
            source.save( debug, mode[ 1 ] )

        #if mode[ 0 ] == win32con.IMAGE_BITMAP:
        #    self.handle = self._winapi_bitmap( source )
        #    return
        
        with tempfile.NamedTemporaryFile( delete = False ) as handle:
            filename = handle.name
            source.save( handle, mode[ 1 ] )

        try:
            self.handle = win32gui.LoadImage( None,
                                              handle.name,
                                              mode[ 0 ],
                                              source.width,
                                              source.height,
                                              win32con.LR_LOADFROMFILE )#| win32con.LR_CREATEDIBSECTION )
        finally:
            os.unlink( filename )

    def __del__( self ):
        # TODO: swap mode to a more descriptive structure
        #
        #self.mode[2]( self.handle )
        pass


class Registry( object ):
    '''
    Registry that maps objects to IDs
    '''
    _objectmap = {}

    _next_id = 1024

    @classmethod
    def register( cls, obj, dst_attr = 'registry_id' ):
        '''
        Register an object at the next available id.
        '''
        next_id = cls._next_id
        cls._next_id = next_id + 1
        cls._objectmap[ next_id ] = obj
        if dst_attr:
            setattr( obj, dst_attr, next_id )
            
    @classmethod
    def lookup( cls, registry_id ):
        '''
        Get a registered action by id, probably for invoking it.
        '''
        return cls._objectmap[ registry_id ]

    class AutoRegister( object ):
        def __init__( self, *args ):
            '''
            Register subclasses at init time.
            '''
            Registry.register( self, *args )

        def lookup( self, registry_id ):
            return Registry.lookup( self, registry_id )

class Action( Registry.AutoRegister ):
    '''
    Class binding a string id to numeric id, op, and action, allowing
    WM_COMMAND etc to be easily mapped to gui-o-matic protocol elements.
    '''


    def __init__( self, gui, identifier, label, operation = None, sensitive = False, args = None ):
        '''
        Bind the action state to the gui for later invocation or modification.
        '''
        super( Action, self ).__init__()
        self.gui = gui
        self.identifier = identifier
        self.label = label
        self.operation = operation
        self.sensitive = sensitive
        self.args = args

    def get_id( self ):
        return self.registry_id

    def __call__( self, *args ):
        '''
        Apply the bound action arguments
        '''
        assert( self.sensitive )
        self.gui._do( op = self.operation, args = self.args )


class Window( object ):
    '''
    Window class: Provides convenience methods for managing windows. Also globs
    systray icon display functionality, since that has to hang off a window/
    windproc. Principle methods:
    
        - set_visiblity( True|False )
        - set_size( x, y, width, height )
        - get_size() -> ( x, y, width, height )
        - set_systray( icon|None, hovertext )   # None removes systray icon
        - set_menu( [ Actions... ] )            # for systray
        - set_icon( small_icon, large_icon )    # window and taskbar

    Rendering:
        Add Layer objects to layers list to have them rendered on WM_PAINT.
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

    class Layer( object ):
        '''
        Abstract base for something to be rendered in response to WM_PAINT.
        Implement __call__ to update the window as desired.
        '''

        @staticmethod
        def intersect( rect_a, rect_b ):
            
            x_min = max(rect_a[0], rect_b[0])
            y_min = max(rect_a[1], rect_b[1])
            x_max = min(rect_a[2], rect_b[2])
            y_max = min(rect_a[3], rect_b[3])
            return (x_min,
                    y_min,
                    x_max,
                    y_max)

        def __call__( self, window, hdc, paint_struct ):
            raise NotImplementedError

    class ImageBlendLayer( Layer ):
        '''
        Manually blends an image with the window, pixel by pixel, using alpha.
        Pros:
          - Works.
        Cons:
          - Slow!
        TODO:
          - Check out rendering everything in PIL, then shipping to winapi as RGB.
              - win32gui.LoadImage() won't open RGBA, alpha is primarily GDI+.
              - Could optionally grab prior window contents.
          - Maybe modidy win32gui.CreateBitmap() to accept an initial byte sequence?
        Wanted:
          - Limit blending to ROI.
          - Handle interrupted rendering better.
          - Handle sizing/stretching better.
        '''

        def __init__( self, image, src_offset = (0,0), dst_offset = (0,0), size = None ):
            self.image = image
            self.src_offset = src_offset 
            self.dst_offset = dst_offset
            self.size = size or image.size
            self.pixels = image.load()

        def _baseline_benchmark( self, window, hdc, paint_struct ):
            '''
            Test pixel access performance without blending.
            Result: About the same as blending.
            '''
            for x in range(self.size[0]):
                for y in range(self.size[1]):
                    dst_x = x + self.dst_offset[0]
                    dst_y = y + self.dst_offset[1]
                    packed = win32gui.GetPixel( hdc, dst_x, dst_y )
                    win32gui.SetPixel( hdc, dst_x, dst_y, 0 )

        def __call__( self, window, hdc, paint_struct ):
            '''
            Blend image per pixel. Inlined everything in integer math
            to reduce python overhead, almost as fast as baseline
            benchmark.
            '''
            # Clip to draw ROI
            roi = paint_struct[ 2 ]
            target = (self.dst_offset[ 0 ],
                      self.dst_offset[ 1 ],
                      self.dst_offset[ 0 ] + self.size[ 0 ],
                      self.dst_offset[ 1 ] + self.size[ 1 ])
            overlap = self.intersect( roi, target )

            x_range = (overlap[ 0 ] - self.dst_offset[ 0 ],
                       overlap[ 2 ] - self.dst_offset[ 0 ])

            y_range = (overlap[ 1 ] - self.dst_offset[ 1 ],
                       overlap[ 3 ] - self.dst_offset[ 1 ])

            # Blend inside ROI
            try:
                for y in range(*y_range):
                    for x in range(*x_range):
                        dst_x = x + self.dst_offset[0]
                        dst_y = y + self.dst_offset[1]
                        src_x = x + self.src_offset[0]
                        src_y = y + self.src_offset[1]
                        original = win32gui.GetPixel( hdc, dst_x, dst_y )
                        src_r = (original >> 0) & 255
                        src_g = (original >> 8) & 255
                        src_b = (original >> 16) & 255
                        mix_r, mix_g, mix_b, alpha = self.pixels[ src_x, src_y ]
                        complement = 255 - alpha
                        dst_r = (src_r * complement + mix_r * alpha) / 255
                        dst_g = (src_g * complement + mix_g * alpha) / 255
                        dst_b = (src_b * complement + mix_b * alpha) / 255
                        result = (dst_b << 16) | (dst_g << 8) | (dst_r << 0)
                        win32gui.SetPixel( hdc, dst_x, dst_y, result )

            # If part of the window becomes occluded during drawing, an
            # exception is thrown.
            #
            except Exception as e:
                traceback.print_exc()    

    class BitmapLayer( Layer ):
        '''
        Stretch a bitmap across an ROI. May no longer be useful...
        '''

        def __init__( self, bitmap, src_roi = None, dst_roi = None, blend = None ):
            self.bitmap = bitmap
            self.src_roi = src_roi
            self.dst_roi = dst_roi
            self.blend = blend
            

        def __call__( self, window, hdc, paint_struct ):
            src_roi = self.src_roi or (0, 0, self.bitmap.size[0], self.bitmap.size[1])
            dst_roi = self.dst_roi or win32gui.GetClientRect( window.window_handle )
            blend = self.blend or (win32con.AC_SRC_OVER, 0, 255, win32con.AC_SRC_ALPHA )

            hdc_mem = win32gui.CreateCompatibleDC( hdc )
            prior = win32gui.SelectObject( hdc_mem, self.bitmap.handle )

            # Blit with alpha channel blending
            win32gui.AlphaBlend( hdc,
                                 dst_roi[ 0 ],
                                 dst_roi[ 1 ],
                                 dst_roi[ 2 ],
                                 dst_roi[ 3 ],
                                 hdc_mem,
                                 src_roi[ 0 ],
                                 src_roi[ 1 ],
                                 src_roi[ 2 ],
                                 src_roi[ 3 ],
                                 blend )
            '''
            # Blit without alpha channel blending
            win32gui.StretchBlt( hdc,
                                 dst_roi[ 0 ],
                                 dst_roi[ 1 ],
                                 dst_roi[ 2 ],
                                 dst_roi[ 3 ],
                                 hdc_mem,
                                 src_roi[ 0 ],
                                 src_roi[ 1 ],
                                 src_roi[ 2 ],
                                 src_roi[ 3 ],
                                 win32con.SRCCOPY )'''
            
            win32gui.SelectObject( hdc_mem, prior )
            win32gui.DeleteDC( hdc_mem )


    class TextLayer( Layer ):
        '''
        Stub text layer, need to add font handling.
        '''

        def __init__( self, text, rect, style = win32con.DT_SINGLELINE, font = None ):
            #win32gui.FillRect( hdc, paintStruct[2], win32con.COLOR_WINDOW )
            self.text = text
            self.rect = rect
            self.style = style
            self.font = font
            self.height = None
            self.roi = None

        def calc_roi( self, hdc ):
            '''
            Figure out where text is actually drawn given a rect and a hdc.

            DT_CALCRECT disables drawing and updates the width parameter of the
            rectangle(but only width!)

            Use DT_LEFT, DT_RIGHT, DT_CENTER and DT_TOP, DT_BOTTOM, DT_VCENTER
            to back out actual roi.
            '''

            if self.font:
                original_font = win32gui.SelectObject( hdc, self.font )
            
            # Height from DT_CALCRECT is strange...maybe troubleshoot later...
            #height, roi = win32gui.DrawText( hdc,
            #                                  self.text,
            #                                  len( self.text ),
            #                                  self.rect,
            #                                  self.style | win32con.DT_CALCRECT )
            #self.width = roi[2] - roi[0]
            #print "roi {}".format( (self.width, self.height) )
                
            (self.width, self.height) = win32gui.GetTextExtentPoint32( hdc, self.text )

            if self.font:
                win32gui.SelectObject( hdc, original_font )

            # Resolve text style against DC alignment
            #
            align = win32gui.GetTextAlign( hdc )

            if self.style & win32con.DT_CENTER:
                horizontal = win32con.TA_CENTER
            elif self.style & win32con.DT_RIGHT:
                horizontal = win32con.TA_RIGHT
            elif self.style & win32con.DT_LEFT:
                horizontal = win32con.TA_LEFT
            else:
                horizontal = align & ( win32con.TA_LEFT | win32con.TA_RIGHT | win32con.TA_CENTER )

            if self.style & win32con.DT_VCENTER:
                vertical = win32con.VTA_CENTER
            elif self.style & win32con.DT_BOTTOM:
                vertical = win32con.TA_BOTTOM
            elif self.style & win32con.DT_TOP:
                vertical = win32con.TA_TOP
            else:
                vertical = align & ( win32con.TA_TOP | win32con.TA_BOTTOM | win32con.VTA_CENTER )

            # Calc ROI from resolved alignment
            #
            if horizontal == win32con.TA_CENTER:
                x_min = (self.rect[ 2 ] + self.rect[ 0 ] - self.width)/2
                x_max = x_min + self.width
            elif horizontal == win32con.TA_RIGHT:
                x_min = self.rect[ 2 ] - self.width
                x_max = self.rect[ 2 ]
            else: # horizontal == win32con.TA_LEFT
                x_min = self.rect[ 0 ]
                x_max = self.rect[ 0 ] + self.width

            if vertical == win32con.VTA_CENTER:
                y_min = (self.rect[ 1 ] + self.rect[ 3 ] - self.height)/2
                y_max = y_min + self.height
            elif vertical == win32con.TA_BOTTOM:
                y_min = self.rect[ 3 ] - self.height
                y_max = self.rect[ 3 ]
            else: # vertical == win32con.TA_TOP
                y_min = self.rect[ 1 ]
                y_max = self.rect[ 1 ] + self.height
    
            self.roi = (x_min, y_min, x_max, y_max)

        def __call__( self, window, hdc, paint_struct ):
            if self.font:
                prior_font = win32gui.SelectObject( hdc, self.font )

            self.calc_roi( hdc )

            prior_bk_mode = win32gui.SetBkMode( hdc, win32con.TRANSPARENT )
            
            win32gui.DrawText( hdc,
                               self.text,
                               len( self.text ),
                               self.rect,
                               self.style )

            win32gui.SetBkMode( hdc, prior_bk_mode )

            if self.font:
                win32gui.SelectObject( hdc, prior_font )

    class Control( Registry.AutoRegister ):
        '''
        Base class for controls based subwindows (common controls)
        '''

        _next_control_id = 1024

        def __init__( self ):
            super( Window.Control, self ).__init__()
            self.action = None

        def __call__( self, window, message, wParam, lParam ):
            print "Not implemented __call__ for " + self.__class__.__name__

        def __del__( self ):
            if hasattr( self, 'handle' ):
                win32gui.DestroyWindow( self.handle )

        def set_size( self, rect ):
            win32gui.MoveWindow( self.handle,
                                 rect[ 0 ],
                                 rect[ 1 ],
                                 rect[ 2 ],
                                 rect[ 3 ],
                                 True )

            
        def set_action( self, action ):
            win32gui.EnableWindow( self.handle, action.sensitive )
            win32gui.SetWindowText( self.handle, action.label )
            self.action = action

    class Button( Control ):

        def __init__( self, parent, rect, action ):
            super( Window.Button, self ).__init__()

            style = win32con.WS_TABSTOP | win32con.WS_VISIBLE | win32con.WS_CHILD | win32con.BS_DEFPUSHBUTTON
            
            self.handle = win32gui.CreateWindowEx( 0,
                                                   "BUTTON",
                                                   action.label,
                                                   style,
                                                   rect[ 0 ],
                                                   rect[ 1 ],
                                                   rect[ 2 ],
                                                   rect[ 3 ],
                                                   parent.window_handle,
                                                   self.registry_id,
                                                   win32gui.GetModuleHandle(None),
                                                   None )
            self.set_action( action )
            
        def __call__( self, window, message, wParam, lParam ):
            self.action( window, message, wParam, lParam )            
                                                   

    class ProgressBar( Control ):
        # https://msdn.microsoft.com/en-us/library/windows/desktop/hh298373(v=vs.85).aspx
        #
        def __init__( self, parent ):
            super( Window.ProgressBar, self ).__init__()
            rect = win32gui.GetClientRect( parent.window_handle )
            yscroll = win32api.GetSystemMetrics(win32con.SM_CYVSCROLL)
            self.handle = win32gui.CreateWindowEx( 0,
                                                   commctrl.PROGRESS_CLASS,
                                                   None,
                                                   win32con.WS_VISIBLE | win32con.WS_CHILD,
                                                   rect[ 0 ] + yscroll,
                                                   (rect[ 3 ]) - 2 * yscroll,
                                                   (rect[ 2 ] - rect[ 0 ]) - 2*yscroll,
                                                   yscroll,
                                                   parent.window_handle,
                                                   self.registry_id,
                                                   win32gui.GetModuleHandle(None),
                                                   None )


        def set_range( self, value ):
            win32gui.SendMessage( self.handle,
                                  commctrl.PBM_SETRANGE,
                                  0,
                                  win32api.MAKELONG( 0, value ) )
        def set_step( self, value ):
            win32gui.SendMessage( self.handle, commctrl.PBM_SETSTEP, int( value ), 0 )

        def set_pos( self, value ):
            win32gui.SendMessage( self.handle, commctrl.PBM_SETPOS, int( value ), 0 )

    @classmethod
    def _make_window_class_name( cls ):
        result = "window_class_{}".format( cls._next_window_class_id )
        cls._next_window_class_id += 1
        return result

    _notify_event_id = win32con.WM_USER + 22

    def __init__(self, title, style,
                 size = (win32con.CW_USEDEFAULT,
                         win32con.CW_USEDEFAULT),
                 messages = {}):
        '''Setup a window class and a create window'''
        self.layers = []
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
            size[ 0 ],
            size[ 1 ],
            None,
            None,
            self.module_handle,
            None )
        
    def set_visibility( self, visibility  ):
        state = win32con.SW_SHOW if visibility else win32con.SW_HIDE
        win32gui.ShowWindow( self.window_handle, state )
        win32gui.UpdateWindow( self.window_handle )


    def get_size( self ):
        return win32gui.GetWindowRect( self.window_handle )

    def get_client_region( self ):
        return win32gui.GetClientRect( self.window_handle )

    def set_size( self, rect ):
        win32gui.MoveWindow( self.window_handle,
                             rect[ 0 ],
                             rect[ 1 ],
                             rect[ 2 ],
                             rect[ 3 ],
                             True )

    @staticmethod
    def screen_size():
        return tuple( map( win32api.GetSystemMetrics,
                           (win32con.SM_CXVIRTUALSCREEN,
                            win32con.SM_CYVIRTUALSCREEN)))

    def center( self ):
        rect = self.get_size()
        screen_size = self.screen_size()
        rect = ((screen_size[ 0 ] - rect[ 2 ])/2,
                (screen_size[ 1 ] - rect[ 3 ])/2,
                rect[ 2 ],
                rect[ 3 ])
        self.set_size( rect )

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
        #print( "{}: {}".format( lookup[ message ], data ) )

        self.systray = True if small_icon else False

        if message is not None:
            win32gui.Shell_NotifyIcon( message, data )

    def set_menu( self, actions ):
        self.menu_actions = actions

    def _on_command( self, window_handle, message, wparam, lparam ):
        target_id = win32gui.LOWORD(wparam)
        print( "command {}".format( target_id ) )
        target = Registry.lookup( target_id )
        target( self, message, wparam, lparam )
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
        (hdc, paint_struct) = win32gui.BeginPaint( self.window_handle )
        for layer in self.layers:
            layer( self, hdc, paint_struct )
        win32gui.EndPaint( self.window_handle, paint_struct )
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
      - Menu items: We'll have to manage associations
        between menu items, actions, and all that: For an item ID (gui-o-matic
        protocol), we'll have to track menu position, generate a winapi command
        id, and catch/map associated WM_COMMAND event back to actions. This
        allows us to toggle sensitivity, replace text, etc.
    """

    _variable_re = re.compile( "%\(([\w]+)\)s" )

    _progress_range = 1000

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

    def layout_displays( self ):
        pass

    def layout_buttons( self ):
        '''
        layout buttons, assuming the config declaration is in order.
        '''
        def button_items():
            button_keys = map( lambda item: item['id'],
                               self.config['main_window']['actions'] )
            return map( lambda key: self.items[ key ], button_keys )
        window_size = self.main_window.get_client_region()

        # Layout left to right across the bottom
        spacing = 10
        min_width = 20
        min_height = 20
        x_offset = window_size[0] + spacing
        y_offset = window_size[3] - window_size[1] - spacing
        x_limit = window_size[2]

        for index, item in enumerate( button_items() ):
            action = item[ 'action' ]
            button = item[ 'control' ]
            
            hdc = win32gui.GetDC( button.handle )
            width, height = win32gui.GetTextExtentPoint32( hdc, action.label )
            win32gui.ReleaseDC( None, hdc )
            
            
            width = max( width + spacing , min_width )
            height = max( height + spacing, min_height )

            # create new row if wrapping needed(not well tested)
            if x_offset + width > x_limit:
                x_offset = window_size[0] + spacing
                y_offset -= spacing + height

            rect = (x_offset,
                    y_offset - height,
                    width,
                    height)
            #print rect
            button.set_size( rect )
            x_offset += width + spacing

        # Force buttons to refresh overlapped regions
        for item in button_items():
            button = item[ 'control' ]
            win32gui.InvalidateRect( button.handle, None, False )

    def create_action( self, control_factory, item ):
        action = Action( self,
                         identifier = item['id'],
                         label = item['label'],
                         operation = item.get('op'),
                         args = item.get('args'),
                         sensitive = item.get('sensitive', False))
        control = control_factory( action )
        self.items[action.identifier] = dict( action = action, control = control )

    def create_menu_control( self, action ):
        return None

    def create_button_control( self, action ):
        control = Window.Button( self.main_window, (10,10,100,30), action )
        return control

    def create_controls( self ):
        '''
        Grab all the controls (actions+menu items) out of the config
        and instantiate them. self.items contains action+control pairs
        for each item.
        '''
        # menu items
        for item in self.config['indicator']['menu']:
            self.create_action( self.create_menu_control, item )

        menu_items = [ self.items[ item['id'] ]['action'] for item in self.config['indicator']['menu'] ]
        self.systray_window.set_menu( menu_items )

        # actions
        for item in self.config['main_window']['actions']:
            self.create_action( self.create_button_control, item )

        self.layout_buttons()

    def create_font( self, points = 0, family = None, bold = False, italic = False ):
        '''
        Create font objects for configured fonts
        '''
        font_config = win32gui.LOGFONT()
        font_config.lfHeight = points
        font_config.lfWidth = 0
        font_config.lfWeight = win32con.FW_BOLD if bold else win32con.FW_NORMAL
        font_config.lfItalic = italic
        font_config.lfCharSet = win32con.DEFAULT_CHARSET
        font_config.lfOutPrecision = win32con.OUT_DEFAULT_PRECIS
        font_config.lfClipPrecision = win32con.CLIP_DEFAULT_PRECIS
        font_config.lfQuality = win32con.ANTIALIASED_QUALITY
        font_config.lfPitchAndFamily = win32con.DEFAULT_PITCH | win32con.FF_DONTCARE

        if family and family not in self.known_fonts:
            print "Unknown font: '{}', using '{}'".format( family, self.default_font )
            
        font_config.lfFaceName =  family if family in self.known_fonts else self.default_font

        return win32gui.CreateFontIndirect( font_config )

    def create_fonts( self ):
        '''
        Create all font objects
        '''
        self.known_fonts = {}
        def handle_font( font_config, text_metric, font_type, param ):
            print font_config.lfFaceName
            self.known_fonts[ font_config.lfFaceName ] = font_config
            return True

        hdc = win32gui.GetWindowDC( self.main_window.window_handle )
        print "=== begin availalbe fonts ==="
        win32gui.EnumFontFamilies( hdc, None, handle_font, None )
        print "=== end available fonts ==="
        self.default_font = win32gui.GetTextFace( hdc )
        print "Default font: " + self.default_font
        
        win32gui.ReleaseDC( self.main_window.window_handle, hdc )
        keys = ( 'title', 'details', 'notification', 'splash' )
        font_config = self.config.get( 'font_styles', {} )
        self.fonts = { key: self.create_font( **font_config.get(key, {}) ) for key in keys }

    class StatusDisplay( object ):

        def __init__( self, id, icon, title, details, gui ):
            self.title = Window.TextLayer( title,
                                           (0,0,0,0),
                                           font = gui.fonts[ 'title' ] )
            self.details = Window.TextLayer( details,
                                           (0,0,0,0),                                   (0,0,0,0),
                                           font = gui.fonts[ 'details' ] )
            self.icon = Window.BitmapLayer( Image.Bitmap( gui.get_image_path( icon ) ) )

            self.id = id

        def layout( self, window, rect ):
            hdc = win32gui.GetWindowDC( window.window_handle )
            self.title.rect = rect
            title_roi = self.title.calc_roi( hdc )
            self.details.rect = (rect[0], title_roi[3], rect[2], rect[3])
            details_roi = self.details.calc_roi( hdc )

            text_height = details_roi[3] - title_roi[1]

            icon_roi = (rect[0],
                        rect[1],
                        rect[0] + text_height,
                        rect[1] + text_height)

            self.icon.dst_roi = icon_roi

            title_roi = (rect[0] + text_height,
                         title_roi[1],
                         rect[2],
                         title_roi[3])

            self.title.rect = title_roi

            details_rect = (rect[0] + text_height,
                            details_roi[1],
                            rect[2],
                            details_roi[3])

            self.details.rect = details_rect
            
            win32gui.ReleaseDC( window.window_handle, hdc )

            return (rect[0],
                    details_rect[3],
                    rect[2],
                    rect[3])

    def create_displays( self ):
        '''
        create status displays and do layout
        '''
        self.displays = { item['id']: self.StatusDisplay( gui = self, **item ) for item in self.config['main_window']['status_displays'] }

    def run( self ):
        '''
        Initialize GUI and enter run loop
        '''
        # https://stackoverflow.com/questions/1551605/how-to-set-applications-taskbar-icon-in-windows-7/1552105#1552105
        #
        self.appid = unicode( uuid.uuid4() )
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(self.appid)
        win32gui.InitCommonControls()
            
        self.systray_window = Window(title = self.config['app_name'],
                                     style = Window.systray_style)

       

        window_size = ( self.config['main_window']['width'],
                        self.config['main_window']['height'] )
        
        self.main_window = Window(title = self.config['app_name'],
                                  style = Window.main_window_style,
                                  size = window_size )

        # need a window to query available fonts
        self.create_fonts()
        self.create_displays()
        
        window_roi = win32gui.GetClientRect( self.main_window.window_handle )
        window_size = tuple( window_roi[2:] )
        try:
            background_path = self.get_image_path( self.config['main_window']['image'] )
            bitmap = Image.Bitmap( background_path, size = window_size, debug = 'debug.bmp' )
            background = Window.BitmapLayer( bitmap )
            self.main_window.layers.append( background )
        except KeyError:
            pass

        self.notification_text = Window.TextLayer( text = '',
                                            rect = self.main_window.get_client_region(),
                                            font = self.fonts['notification'])

        self.main_window.layers.append( self.notification_text )
        
        self.main_window.set_visibility( self.config['main_window']['show'] )
        
        self.splash_screen = Window(title = self.config['app_name'],
                                    style = Window.splash_screen_style,
                                    size = window_size )

        self.windows = [ self.main_window,
                         self.splash_screen,
                         self.systray_window ]

        self.set_status( 'normal' )

        self.create_controls()

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

    def set_status(self, status='startup', badge = 'ignored'):
        icon_path = self._resolve_variables( self.config['images'][status] )
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

    def set_item(self, id=None, label=None, sensitive = None):
        action = self.items[id]['action']
        if label:
            action.label = label
        if sensitive is not None:
            action.sensitive = sensitive
            
        control = self.items[id]['control']
        if control:
            control.set_action( action )
            self.layout_buttons()
        
    def set_status_display(self, id=None, title=None, details=None, icon=None, color=None):
        pass

    def update_splash_screen(self, message=None, progress=None):
        if progress:
            self.progress_bar.set_pos( self._progress_range * progress )
        if message:
            self.splash_text.text = message
            print "redraw: {}".format( self.splash_text.roi )
            win32gui.InvalidateRect( self.splash_screen.window_handle,
                                     self.splash_text.roi,
                                     True )

    def set_next_error_message(self, message=None):
        self.next_error_message = message

    def get_image_path( self, name ):
        prefix = 'image:'
        if name.startswith( prefix ):
            key = name[ len( prefix ): ]
            name = self.config['images'][ key ]
        return self._resolve_variables( name )

    def show_splash_screen(self, height=None, width=None,
                           progress_bar=False, image=None,
                           message='', message_x=0.5, message_y=0.5):
        # TODO: Handle height/width as None
        window_roi = win32gui.GetClientRect( self.splash_screen.window_handle )
        window_size = tuple( window_roi[2:] )
        
        #bitmap = Image.Bitmap( self.get_image_path( image ),
        #                       size = window_size )
        #background = Window.BitmapLayer( bitmap )
        
        image = PIL.Image.open( self.get_image_path( image ) )
        image = image.convert('RGBA')
        image = image.resize( window_size, PIL.Image.ANTIALIAS )

        self.splash_text = Window.TextLayer( message,
                                             window_roi,
                                             style = win32con.DT_SINGLELINE |
                                                     win32con.DT_CENTER |
                                                     win32con.DT_VCENTER,
                                             font = self.fonts['splash'] )
        
        self.splash_screen.layers = [ Window.ImageBlendLayer( image ),
                                      self.splash_text ]

        if progress_bar:
            self.progress_bar = Window.ProgressBar( self.splash_screen )
            self.progress_bar.set_range( self._progress_range )
            self.progress_bar.set_step( 1 )

        self.splash_screen.center()
        self.splash_screen.set_visibility( True )

    def hide_splash_screen(self):
        self.splash_screen.set_visibility( False )
        if hasattr( self, 'progress_bar' ):
            del self.progress_bar

    def show_main_window(self):
        self.main_window.set_visibility( True )

    def hide_main_window(self):
        self.main_window.set_visibility( False )

    def _report_error(self, e):
        traceback.print_exc()
        self.notify_user(
                (self.next_error_message or 'Error: %(error)s')
                % {'error': unicode(e)})

    def notify_user(self, message, popup=False, alert = False, actions = []):
        self.notification_text.text = message
        win32gui.InvalidateRect( self.main_window.window_handle,
                                 self.notification_text.roi,
                                 True )
        print('NOTIFY: %s' % message)

GUI = WinapiGUI
