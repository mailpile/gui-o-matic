# The GUI-o-Matic Protocol

GUI-o-Matic implements a relatively simple protocol for communicating
between the main application and the GUI tool.

There are three main stages to the protocol:

   1. Configuration
   2. Handing Over Control
   3. Ongoing GUI Updates

The protocol is a one-way stream of text (ASCII/JSON), and is line-based
and case sensitive at all stages.

The initial stream should be read from standard input, a file, or by
capturing the output of another tool.

Conceptually, stages 2 and 3 are separate because they accomplish very
different things, but in practice they overlap; the source of the protocol
stream may change at any time after stage 1.

Note: There's no strong reason stages 1, 2 and 3 use different syntax;
mostly I think it looks nicer this way and makes it easy to read and
write raw command transcripts. Similar things look similar, different things
look different!


-----------------------------------------------------------------------------
## 1. Configuration

The first stage uses the simplest protocol, but communicates the richest set
of data: at this stage the GUI-o-Matic tool simply reads a JSON-formatted
dictionary. The dictionary defines the main characteristics of our user
interface.

GUI-o-Matic should read until it sees a line starting with the words `OK GO`
or `OK LISTEN`, at which point it should attempt to parse the JSON structure
and then proceed to stage two.

When the configuration dictionary is parsed, it should be treated in the
forgiving spirit of JSON in general: most missing fields should be replaced
with reasonable defaults and unrecognized fields should be ignored.

The following is an example of a complete configuration dictionary, along
with descriptions of how it is interpreted.

**Note:** Lines beginning with a `#` are comments explaining what each
section means. They should be omitted from any actual implementation
(comments are sadly not legal in JSON).

    {
        # Basics
        "app_name": "Your App Name",
        "app_icon": "/reference/or/path/to/icon.png",

        # These are for testing only; implementations may ignore them.
        "_require_gui": ["unity", "macosx", "gtk"],
        "_prefer_gui": ["unity", "macosx", "gtk"],

        # HTTP Cookie { key: value, ... } pairs, by domain.
        # These get sent as cookies along with get_url/post_url HTTP requests.
        "http_cookies": {
            "localhost:33411": {
                "session": "abacabadonk"
            }
        },
    ...

The `images` section defines a dictionary of named icons/images. The names can
be used directly by the `set_status` method, or anywhere an icon path can be
provided by using the syntax `image:NAME` instead.

The only required entry is `normal`.

There is also preliminary support for light/dark/... themes, by embedding the
magic marker `%(theme)s` in the name. The idea is that if the backend somehow
detects that a dark theme is more appropriate, it will replace `%(theme)s` with
the word `dark`. The current draft OS X backend requests an `osx` theme because
at some point Mac OS X needed slightly different icons from the others.

    ...
        "images": {
            "normal": "/path/to/%(theme)s/normal.svg",
            "flipper": "/path/to/unthemed/flipper.png",
            "flopper": "/path/to/flop-%(theme)s.png"
            "background": "/path/to/a/nice/background.jpg"
        },
    ...

In `font_styles`, we define font styles used in different parts of the app.

    ...
        "font_styles": {
            # Style used by status display titles in the main window
            "title": {
                "family": "normal",
                "points": 18,
                "bold": True
            },

            # Style used by status display details in the main window
            "details": {
                "points": 10,
                "italic": True
            },

            # The main-window may have a standalone notification element,
            # for messages that don't go anywhere else.
            "notification": { ... },

            # The progress reporting label on the splash screen
            "splash": { ... }
        },
    ...

The `main_window` section defines the main app window. The main app window has
the following elements:

   * Status displays (an icon and some text: title + details)
   * Actions (buttons or menu items)
   * A notification display element (text label)
   * A background image

How these are actually laid out is up to the GUI backend. Desktop platforms
should largely behave the same way, but we could envision a mobile (android?)
implementation that for example ignored the width/height parameters and moved
some of the actions to a hamburger "overflow" menu.

    ...
        "main_window": {
            # Is the main window displayed immediately on startup? This
            # will be set to False when we are using a splash-screen.
            "show": False,

            # If True, closing the main window exits the app. If False,
            # it just hides the main window, and we rely on the indicator
            # or other mechanisms to bring it back as necessary.
            "close_quits": False,

            # Recommended height/width. May be ignored on some platforms.
            "width": 550,
            "height": 330,

            # Background image.  May be ignored on some platforms.
            "background": "image:background",

            # Default notification label text
            "initial_notification": "",
    ...

The `status_displays` in the main window are used to communicate both visual
and textual clues about different things. Each consists of an icon, a main
label and a hint. The values provided are defaults, all are likely to change
later on. The GUI backend has a fair bit of freedom in how it renders these,
but order should be preserved and labels should be made more prominent than
hints.

    ...
            "status_displays": [
                {
                    "id": "internal-identifying-name",
                    "icon": "image:something",
                    "title": "Hello world!",
                    "details": "Greetings and salutations to all!"
                },{
                    "id": "id2",
                    "icon": "/path/to/some/icon.png",
                    "title": "Launching Frobnicator",
                    "details": "The beginning and end of all things"
                }
            ],
    ...

The main window `actions` are generally implemented as buttons in desktop
environments. Actions are to be allocated space in the GUI, in the order they
are specified - if we run out of space, latter actions may be moved to some
sort of overflow or "hamburger".

The `position` field gives a clue about ordering on the display itself, but
does not influence priority. As an example, in a typical left-to-right row of
buttons, the first action to request `last` should be rendered furthest to the
right, and the first action to request `first` furthest to the left.  Latter
buttons get rendered progressively closer to the middle, until we run out of
space. Adjust accordingly if the buttons are rendered top-to-bottom (portrait
mode on mobile?).

The `op` and `args` fields together define what happens if the user clicks the
button. The operation can be any of the Stage 3 operations defined below, in
which case "args" should be a dictionary of arguments, or it can be one of:
`show_url`, `get_url`, `post_url`, or `shell`. See below for further
clarifications on these ops and their arguments.

    ...
            "actions": [
                {
                    "id": "open",
                    "type": "button",  # button is the default
                    "position": "first",
                    "label": "Open",
                    "op": "show_url",
                    "args": "http://www.google.com/"
                },{
                    "id": "evil666",
                    "position": "last",
                    "label": "Harakiri",
                    "op": "shell",
                    "args": ["rm -rf /ha/ha/just/kidding",
                             "echo 'That was close'"]
                }
            ]
        # The "main_window" example ends here
        },
    ...

The final section of the configuration is the `indicator`, which ideally is
implemented as a mutable icon and action menu, displayed in the appropriate
place on the Desktop (top-bar on the mac? system tray on Windows?). If no
such placement is possible, the indicator may instead show up as an icon
in the main window itself.

The menu items should be rendered in the order specified.

Items in the menu with `sensitive` set to false should be displayed, but
not clickable by the user (greyed out). Note that the label text and
sensitivity of an item may later be modified by Stage 3 commands.

Menu items may also be separators, which in most environments draws a
horizontal dividor. Environments not supporting that may use a blank menu
item instead, or omit, as deemed appropriate.

Within these menus, the `id`, `op` and `args` fields have the same
meanings and function as they do in the main window actions. Configuration
writes should take care to avoid collissions when chosing item IDs.

An menu item with the ID `notification` is special and should receive text
updates from the `notify_user` method.

        "indicator": {
            "initial_status": "startup",  # Should match an icon
            "menu_items": [
                {
                    "id": "notification",
                    "label": "Starting up!",
                    "sensitive": False
                },{
                    "separator": True
                },{
                    "id": "xkcd",
                    "label": "XKCD is great",
                    "op": "show_url",
                    "args": "https://xkcd.com/"
                }
            ]
        }
    }

There are more examples in the [scripts/](scripts) folder!


### Operations and arguments

Both main-window actions and indicator menu items specify `op` and `args`
to define what happens when the user clicks on them.

These actions are either GUI-o-Matic Stage 3 operations (in which case `args`
should be a dictionary of arguments), web actions, or a shell command.

In all cases, execution (or network) errors result in a notification being
displayed to the user.

**FIXME:** It should be possible to customize the error messages...


#### Web Actions: `show_url`

The most basic web action is `show_url`. This action takes a single argument,
which is the URL to display. The JSON structure may be any of: a string, a
list with a single element (the string) or a dictionary with a `_url`.

No cookies or POST data can be specified with this method. When activated, this
operation should request the given URL be opened in the user's default browser.

**FIXME:** In a new tab? Or reuse a tab we already opened? Make this configurable
by adding args to a dictionary?


#### Web Actions: `get_url`, `post_url`

These actions will in the background send an HTTP GET or HTTP POST request
to the URL specified in the argument.

For GET requests, the JSON structure may be any of: a string, a list with a
single element (the string) or a dictionary with a `_url`.

For POST requests, `args` should be a dictionary, where the URL is specified in
an element named `_url`. All other elements in the dictionary will be encoded
as payload/data and sent along with the POST request.

If the response data has the MIME type `application/json`, it parses as a JSON
dictionary, and the JSON has a top-level element named `message`, that result
text will be displayed to the user as a notification.


#### Shell Actions: `shell`

Shell actions expect `args` to be a list of strings. Each string is passed
to the operating system shell as a command to execute (so a single click can
result in multiple shell actions). If any fails (returns a non-zero exit code),
the following commands will not run.

The output from the shell commands is discarded.


-----------------------------------------------------------------------------
## 2. Handing Over Control

The GUI-o-Matic protocol has five options for handing over control (changing
the stream of commands) after the configuration has been processed:

   1. **OK GO** - No more input
   2. **OK LISTEN** - No change, keep reading the same source
   3. **OK LISTEN TO: cmd** - Launch cmd and read its standard output
   4. **OK LISTEN TCP: cmd** - Launch cmd and read from a socket
   5. **OK LISTEN HTTP: url** - Fetch and URL and read from a socket

Options 2.1 and 2.2 are trivial and will not be discussed further.

In all cases except "OK GO", if GUI-o-Matic reaches "end of file" on the
update stream, that should result in shutdown of GUI-o-Matic itself.


### 2.3. OK LISTEN TO

Example: `OK LISTEN TO: cat /tmp/magic.txt`

If the handover command begins with "OK LISTEN TO: ", the rest of the
line should be treated verbatim as something to be passed to the operating
system shell.

The standard output of the spawned command shall be read and parsed for
stage 2 or stage 3 updates.

Errors: The GUI-o-Matic should monitor whether the spawned command
crashes/exits with a non-zero exit code and communicate that to the user.


### 2.4. OK LISTEN TCP

Example: `OK LISTEN TCP: mailpile --www= --gui=%PORT% --wait`

In this case, the GUI-o-Matic must open a new listening TCP socket
(preferably on a random OS-assigned localhost-only port).

The rest of the "OK LISTEN TCP: ..." line should have all occurrances
of `%PORT%` replaced with the port number, and the resulting string
passed to the operating system shell to execute.

The spawned command is expected to connect to `localhost:PORT` and
send further stage 2 or stage 3 updates over that channel.

Errors: In addition to checking the exit code of the spawned process as
described above, GUI-o-Matic should also monitor whether the spawned command
crashes/exits without ever establishing a connection and treat that and
excessive timeouts as error conditions.


### 2.5. OK LISTEN HTTP

Example: `OK LISTEN HTTP: http://localhost:33411/gui/%PORT%/`

This command behaves identically to `OK LISTEN TCP`, except instead of
spawning a new process the app connects to an HTTP server on localhost
and passes information about the control port in the URL.

Again, HTTP errors (non-200 result codes) and socket errors should be
communicated to the user and treated as fatal. The body of the HTTP
reply is ignored.

**TODO:** *An alternate HTTP method which repeatedly long-polls an URL
for commands would allow GUI-o-Matic to easily play nice over the web!
We don't need this today, but it might be nice for someone else? Food for
thought...* **DANGER! This could become a huge security hole!**


-----------------------------------------------------------------------------
## 3. Ongoing GUI Updates

The third stage (which is processed in parallel to stage 2), is commands
which send updates to the GUI itself.

These updates all use the same syntax:

    lowercase_command_with_underscores {"arguments": "as JSON"}

Each command will fit on a single line (no newlines are allowed in
the JSON section) and be terminated by a CRLF or LF sequence. If there
are no arguments, an empty JSON dictionary `{}` is expected.

A description of the existing commands follows; see also
`gui_o_matic/gui/base.py` for the Python definitions.


### show_splash_screen

Arguments:

   * background: (string) path to a background image file
   * message: (string) initial status message
   * progress_bar: (bool) display a progress bar?

This displays a splash-screen, to keep the user happy while something
slow happens.

### update_splash_screen

Arguments:

   * progress: (optional float) progress bar size in the range 0 - 1.0
   * message: (optional string) updated status message

### hide_splash_screen

Arguments: none

Hides the splash-screen.

### show_main_window

Arguments: none

Display the main application window.

### hide_main_window

Arguments: none

Hide the main application window.

### set_status

Arguments:

   * status: "startup", "normal", "working", ...

Sets the overall "status" of the application, which will be displayed by
changing an indicator icon somewhere within the app. All statuses should
have an icon defined in the `images: { ... }` section of the configuration.

### set_status_display

Arguments:

   * id: (string) The ID of the status display section
   * title: (optional string) Updated text for the title label
   * details: (optional string) Updated text for the details label
   * icon: (optional string) FS path or reference to an entry in `images`
   * color: (optional #rgb/#rrggbb string) Color for label text

This will update some or all of the elements of one of the status display
sections in the main window.

### set_item

Arguments:

   * id: (string) The item ID as defined in the configuration
   * label: (optional string) A new label!
   * sensitive: (optional bool) Make item senstive (default) or insensitive

This can be used to change the labels displayed in the indicator menu
(the `indicator: menu: [ ... ]` section of the configuration).

This can also be used to change the sensitivity of one of the entries in the
indicator menu (the `indicator: menu: [ ... ]` section of the config).
Insensitive items are greyed out but should still be displayed, as apps
may choose to use the to communicate low-priority information to the user.


### set_next_error_message

Arguments:

   * message: (optional string) What to say next time something fails

This can be used to override GUI-o-Matic internal error messages (including
those generated by stage 2 commands above). Calling this with no arguments
reverts back to the default behaviour.

This is important to allow apps to give friendlier (albeit less precise)
messages to users, including respecting localization settings in the
controlling app.

### notify_user

Arguments:

   * message: (string) Tell the user something
   * popup: (optional bool) Prefer an OSD/growl/popup style notification

This method should always try and display a message to the user, no matter
which windows are visible:

   * If popus are requested, be intrusive!
   * If the splash screen is visible, display there
   * If the main window is visible, display there
   * ...?

### show_url

Arguments:

   * url: (url) The URL to open

Open the named URL in the user's preferred browser.

**FIXME:** *For access control reasons, this method should support POST, and/or
allow the app to configure cookies. However it's unclear whether the methods
available to us for launching the browser actually support that accross
platforms. Needs further research.*

### terminal

Arguments:

   * command: (string) The shell command to launch
   * title: (optional string) The preferred terminal window title
   * icon: (optional string) FS path or reference to an entry in `images`

Spawn a command in a visible terminal, so the user can interact with it.

### quit

Arguments: none

Shut down GUI-o-Matic.


-----------------------------------------------------------------------------
*The end*
