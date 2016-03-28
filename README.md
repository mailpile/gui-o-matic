# GUI-o-Matic!

This is a tool for creating minimal graphical user interfaces; usually
just a splash screen and an indicator icon with a drop-down menu.

The tool is inspired by `dialog` and other similar command-line
utilities which provide drop-in user interfaces for shell scripts.

GUI-o-matic is also a drop-in UI, but it differs from these tools in
that it is meant to be used as long-running process, either
communicating with a background process (a worker) or providing access
to URLs or shell commands.

Background worker processes can mutate GUI-o-matic's state using a
simple JSON-based protocol, and the GUI can communicate back or perform
actions based on user input in numerous ways. Background workers that
need richer user interfaces than are provided by GUI-o-Matic itself are
expected to expose web- or terminal interfaces which GUI-o-Matic can
launch as necessary.

When used without a worker, GUI-o-Matic can provide easy point-and-click
access to shell commands or URLs (see [example scripts][./scripts/]).

Initally written as part of [Mailpile](https://www.mailpile.is/), this
app is released separately so other projects can make use of it.


## Project Status and License

This project is **a work in progress**. Please feel free to help out!

The license is the GNU LGPL which means it can be used and distributed
along with proprietary applications, but changes to GUI-o-Matic itself
must be shared with the community.


## Getting Started

TODO: Write this!


## Supported Platforms

GUI-o-matic currently supports the following desktop environments:

   * Ubuntu Unity
   * MacOS X (partial)

Ideally, future versions will add support for:

   * Microsoft Windows
   * GNOME
   * KDE
   * Standard X11

If you have experience developing user interface code on any of these
platforms, please consider helping out!


## User Interface

GUI-o-matic currently allows creation of the following UI elements and
behaviours:

   * An indicator with mutable icon and drop-down menu
   * System notifications (growl-style)
   * A splash screen
   * Open URLs in browser
   * Load URLs in background
   * Run shell commands in background

Planned features:

   * Spash screen progress bar
   * Dock icon with mutable icon and custom menu
   * Launch apps in terminal windows

The UI feature-set is deliberately meant to stay small, to increase the
odds that the full functionality can be made available on all platforms.


## Configuration and Communication

On launch, the `gui-o-matic` tool will read a JSON formatted
configuration from standard-input, until it encounters the words `OK GO`
or `OK LISTEN` on a line by themselves.

In GO mode, the app will continue running until killed.

In LISTEN mode, the app will then continue reading standard input,
expecting one command per line. On EOF the app will terminate. The
command format is very simple; a command-name followed by a space and a
single JSON structure for arguments. Examples:

    update_splash_screen {"progress": 0.2, "message": "Yaaay"}

    set_menu_label {"item": "frobnicator", "label": "FROB IT"}

    notify_user {"message": "Hello World!"}

See below for a full list of available commands. The
[scripts](./scripts/) folder contains working examples illustrating
these concepts.


## Credits and license

Copyright 2016, Mailpile ehf. and Bjarni Rúnar Einarsson.

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
