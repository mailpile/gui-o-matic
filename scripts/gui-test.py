#!/usr/bin/python

import os.path
import sys
import subprocess
import time
import copy
import json

def readlink_f( path ):
    while True:
        try:
            path = os.readlink( path )
        except (OSError, AttributeError):
            break
    return os.path.abspath( path )

def format_pod( template, **kwargs ):
    '''
    apply str.format to all str elements of a simple object tree template
    '''
    if isinstance( template, dict ):
        template = { format_pod( key, **kwargs ): format_pod( value, **kwargs ) for (key,value) in template.items() }
    elif isinstance( template, str ):
        template = template.format( **kwargs )
    elif isinstance( template, list ):
        template = [ format_pod( value, **kwargs ) for value in template ]
    elif callable( template ):
        template = format_pod( template(), **kwargs )
    else:
        # Maybe raise an error instead?
        #
        template = copy.copy( template )
        
    return template

class TestSession( object ):
    '''
    Test session for scripting testing gui-o-matic
    '''

    def __init__( self, parameters, log = "test.log" ):
        self.parameters = parameters
        cmd = (sys.executable,'-m','gui_o_matic')
        parentdir = os.path.split( parameters['basedir'] )[0]

        with open( log, "w" ) as handle:
            cwd = os.getcwd()
            os.chdir( parentdir )
            self.proc = subprocess.Popen( cmd, stdin=subprocess.PIPE, stdout=handle, stderr=handle )
            os.chdir( cwd )


    def send( self, text ):
        self.proc.stdin.write( text + '\n' )
        self.proc.stdin.flush()

    def config( self, template ):
        text = json.dumps( format_pod( template, **self.parameters ) )
        self.send( text )

        
    def command( self, command, template):
        text = '{} {}'.format( command,
                               json.dumps( format_pod( template, **self.parameters ) ) )
        self.send( text )


    def close( self ):
        self.proc.stdin.close()
        self.proc.wait()

script = {
    "app_name": "Indicator Test",
    "app_icon": "{basedir}/img/gt-normal-%(theme)s.png",
    "_prefer_gui": ["unity", "macosx", "winapi"],
    "images": {
        "startup": "{basedir}/img/gt-startup-%(theme)s.png",
        "normal": "{basedir}/img/gt-normal-%(theme)s.png",
        "working": "{basedir}/img/gt-working-%(theme)s.png",
        "attention": "{basedir}/img/gt-attention-%(theme)s.png",
        "shutdown": "{basedir}/img/gt-shutdown-%(theme)s.png"
    },
    "font_styles": {
        "title": {
            "family": "normal",
            "points": 18,
            "bold": True
        },
        "details": {
            "points": 10,
            "italic": True
        },
    },
    "main_window": {
        "show": False,
        "initial_notification": "Hello world!\nThis is my message for you.",
        "close_quits": True,
        "width": 480,
        "height": 360,
        "background": "{basedir}/img/gt-wallpaper.png",
        "action_items": [
            {
                "id": "btn-xkcd",
                "label": "XKCD",
                "position": "first",
                "sensitive": False,
                "op": "show_url",
                "args": "https://xkcd.com/"
            },{
                "id": "mp",
                "label": "Mailpile?",
                "position": "first",
                "sensitive": True,
                "op": "terminal",
                "args": {"command": "screen -x -r mailpile || screen"}
            },{
                "id": "quit",
                "label": "Quit",
                "position": "last",
                "sensitive": True,
                "op": "quit"
            }
        ],
        "status_displays": [
            {
                "id": "internal-identifying-name",
                "icon": "image:working",
                "title": "Hello world!",
                "details": "Greetings and salutations to all!"
            },{
                "id": "id2",
                "icon": "image:attention",
                "title": "Launching Frobnicator",
                "details": "The beginning and end of all things...\n...or is it?"
            }
        ]
    },
    "indicator": {
        "menu_items": [
            {
                "label": "Indicator test",
                "id": "info"
            },{
                "separator": True
            },{
                "label": "XKCD",
                "id": "menu-xkcd",
                "op": "show_url",
                "args": ["https://xkcd.com/"],
                "sensitive": False
            },{
                "label": "Mailpile",
                "id": "mailpile",
                "op": "show_url",
                "args": ["https://www.mailpile.is/"],
                "sensitive": True
            }
        ]
    }
}

session = TestSession( parameters = {
    'basedir': os.path.split( readlink_f( sys.argv[ 0 ] ) )[ 0 ]
})

session.config( script )
session.send( "OK LISTEN" )

session.command( 'show_splash_screen',
         {
            "background": "{basedir}/img/gt-splash.png",
            "width": 320,
            "message": "Hello world!",
            "progress_bar": True
         })
time.sleep( 2 )

session.command( 'update_splash_screen', {"progress": 0.2} )
session.command( 'set_status', {"status": "normal"} )
time.sleep( 2 )

session.command( 'update_splash_screen', {"progress": 0.5, "message": "Woohooooo"} )
session.command( 'update_splash_screen', {"progress": 0.5} )
session.command( 'set_item', {"id": "menu-xkcd", "sensitive": True} )
session.command( 'set_item', {"id": "btn-xkcd", "sensitive": True} )
session.command( 'notify_user', {"message": "This is a notification"} )
session.command( 'notify_user', {"message": "This is a popup notification",
                                 "popup": True,
                                 "actions": [{
                                     "op": "show_url",
                                     "label": "XKCD",
                                     "url": "https://xkcd.com"
                                  }]
                                 })
time.sleep( 2 )
session.command( 'set_status', {"badge": ""} )
session.command( 'update_splash_screen', {"progress": 1.0} )
session.command( 'set_status', {"status": "working"} )
time.sleep( 2 )

session.command( 'hide_splash_screen', {} )
session.command( 'show_main_window', {} )
session.command( 'set_status', {"status": "attention"} )
time.sleep( 2 )


session.command( 'set_status_display', {"id": "id2",
                                        "icon":"image:shutdown",
                                        "title": "Whoops!",
                                        "details": "Just kidding!" } )
session.command( 'set_item', {"id": "menu-xkcd", "label": "No really, XKCD"} )
session.command( 'set_item', {"id": "btn-xkcd", "label": "XKCDonk"} )
time.sleep( 30 )

session.command( 'set_status', {"status": "shutdown"} )
time.sleep( 5 )

session.close()
