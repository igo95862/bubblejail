Name
=================

Synopsis
+++++++++++++++++++++

**bubblejail** <command> [options] [targets]

Description
+++++++++++++++++++++

Bubblejail is a bubblewrap based sandboxing application.

Concepts
+++++++++++++++++++++++++++

**Bubblejail's** design is based on observations of **Firejail's** faults.

One of the biggest issues with Firejail is that you can accidentally run
unsandboxed applications and not notice.

**Bubblejail**, instead of trying to transparently overlay an existing
home directory, creates a separate home directory.

Every **Instance** represents a separate home directory.
Typically, every sandboxed application has its own home directory.

Each instance has a ``services.toml`` file which defines the
configuration of the instance such as system resources that the
sandbox should have access to.

**Service** represents some system resources that the sandbox
can be given access to. For example, the Pulse Audio service gives
access to the Pulse Audio socket so that the application can use sound.

**Profile** is a predefined set of services that a particular
application uses. For example, Firefox profiles gives access to
network, pulse audio and ``~/Downloads`` folder. Users can define
their own profiles in ``~/.config/bubblejail/profiles`` directory.

Profiles also specify the desktop entry to copy and MIME types
the application has.

**Bubblejail** uses TOML configuration format.

Commands
+++++++++++++++++++++

bubblejail has the following commands

list [what]
^^^^^^^^^^^^^^^^^^

List something

* 
    **profiles** - List available profiles. There are three places from where profiles are red.
    ``/usr/share/bubblejail/profiles`` for system wide profiles.
    ``$HOME/.config/bubblejail/profiles`` for user defined profiles.

*
    **instances** - List created instances.

*
    **services** - List services.

create [options] [new_instance_name]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creates a new instance. 

When a new instance is created a desktop entry will be also created.

Creating an instance from profile will print some import tips that you
can use to import configuration from unsandboxed application.

Options:

*
    ``--profile [name]`` Specify the profile that the instance will use.
    For available profiles, see the ``list`` command.
    If omitted an empty profile will be used and
    the user will have to define the configuration manually.
    There is also a ``generic`` profile which has some common settings such
    as network and windowing system access.

*
    ``--no-desktop-entry`` Do not create a new desktop entry.

run [options] [instance] [arguments]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run the instance. This launches sandbox and the application inside.

The arguments are optional if you have ``executable_name`` key set in config.

Otherwise, you **must** specify arguments to run. 

The arguments **must** include the program executable. I.E.
``bubblejail run FirefoxInstance firefox google.com``

If the instance already running this command will run the arguments inside
the sandbox. If ``--wait`` option is passed the output of the command
will be returned.

Options:

*
    ``--wait`` Wait on the command inserted in to sandbox and get the output.

*
    ``--debug-shell`` Opens a shell inside the sandbox instead of running program.
    Useful for debugging.

*
    ``--dry-run`` Prints the bwrap and xdg-desktop-entry arguments instead of running.

*
    ``--debug-log-dbus`` Enables dbus proxy logging.

*
    ``--debug-helper-script [script]`` use the specified helper script.
    This is mainly development command.


edit [instance]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Opens the configuration file in the ``EDITOR``.
After exiting the editor, the file is validated and 
only written if validation is successful.

``EDITOR`` environmental variable must be set.

generate-desktop-entry [options] [instance]
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generates a new desktop entry for the instance.

Desktop entry can either be specified by profile, path, name or
extracted from metadata when instance was created.

*
    ``--profile`` use desktop entry specified in profile.

*
    ``--desktop-entry`` use desktop entry name. Can either be an absolute
    path or name (with or without .desktop) which will be searched under
    /usr/share/applications.

See also
+++++++++++++++++++++++++++

Bubblejail home page: https://github.com/igo95862/bubblejail

Bugs
+++++++++++++++++++++++++++

Report bugs to the bugtracker: https://github.com/igo95862/bubblejail/issues
