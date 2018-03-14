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

The first stage is simplest. At this stage the GUI-o-Matic tool simply
reads a JSON-formatted dictionary.

It should read until it sees a line starting with the words "OK GO" or
"OK LISTEN", at which point it should attempt to parse the JSON structure
and then proceed to stage two.

**FIXME:** Better document the configuration structure. In the meantime,
there are examples in the [scripts/](scripts) folder.


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
thought...*


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

   * image: (string) path to a background image file
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
have an icon defined in the `icons: { ... }` section of the configuration.

### set_substatus

Arguments:

   * substatus: (string) The ID of the substatus section
   * label: (optional string) Updated text for the main label
   * hint: (optional string) Updated text for the hint label
   * icon: (optional string) FS path or reference to an entry in `icons`
   * color: (optional #rgb/#rrggbb string) Color for label text

This will update some or all of the elements of one of the substatus
sections in the main window.

### set_item_label

Arguments:

   * item: (string) The item ID as defined in the configuration
   * label: (string) A new label!

This can be used to change the labels displayed in the indicator menu
(the `indicator: menu: [ ... ]` section of the configuration).

### set_item_sensitive

Arguments:

   * item: (string) The item ID as defined in the configuration
   * sensitive: (optional bool) Make item senstive (default) or insensitive

This can be used to change the sensitivity of one of the entries in the
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
   * icon: (optional string) FS path or reference to an entry in `icons`

Spawn a command in a visible terminal, so the user can interact with it.

### quit

Arguments: none

Shut down GUI-o-Matic.


-----------------------------------------------------------------------------
*The end*
