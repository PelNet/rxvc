"""Commands for controlling a Yamaha RX-V series receiver."""
import operator
import click

from rxv.exceptions import ResponseException
import rxvc.cache as cache

CTX_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(invoke_without_command=True,
             no_args_is_help=True,
             context_settings=CTX_SETTINGS)
@click.option('--clear',
              is_flag=True,
              default=False,
              help="Clear the cache and look for receivers again.")
@click.pass_context
def cli(ctx, clear):
    """Control your Yamaha receiver from the command line, really fast.

    Taking advantage of caching (which can be cleared buy running rxvc
    with no command but with --clear), after the first run it's super
    fast. This cache is stored in ~/.rxvc_cache.

    Have fun!

    """
    if clear:
        print("Clearing receiver cache as requested...")
        cache.clear()

    receiver = cache.cached_receiver()
    if receiver is None:
        receiver = cache.find_receiver()
        cache.cache_receiver(receiver)

    ctx.obj = {}
    ctx.obj['avr'] = receiver


@cli.command(context_settings=CTX_SETTINGS)
@click.pass_context
def status(ctx):
    """Print overall status of the receiver."""
    status = ctx.obj['avr'].basic_status
    print(("\nPower: {on}\n"
           "Input: {input}\n"
           "Volume: {volume}\n"
           "Muted: {muted}\n").format(
               on=status.on,
               input=status.input,
               volume=status.volume,
               muted=status.mute))

@cli.command(context_settings=CTX_SETTINGS)
@click.pass_context
def inputs(ctx):
    """List valid input names for this receiver.

    These are names that can also be passed to the input command
    when using it to set an input.

    """
    for input in sorted(ctx.obj['avr'].inputs()):
        print('* ', input)


@cli.command(context_settings=CTX_SETTINGS)
@click.argument("input", nargs=-1)
@click.pass_context
def input(ctx, input):
    """See the current receiver input or set it if passed an
    argument that is a valid input for the receiver. Note that
    if it has spaces in it, you should wrap the whole argument
    in quotes.

    """
    avr = ctx.obj['avr']
    if input:
        if input[0] in avr.inputs():
            print("Setting receiver input to {}".format(input[0]))
            avr.input = input[0]
        else:
            print(("That's not a valid input. Run `rxvc inputs' to"
                   "get a list of them."))
    else:
        print("Current input is", avr.input)


@cli.command(context_settings=CTX_SETTINGS)
@click.argument("output", required=True)
@click.argument("state", required=True)
@click.pass_context
def output(ctx, output, state):
    """Set the outputs of the receiver on or off.

    """
    avr = ctx.obj['avr']
    if state in ['on', 'off']:
        if (state == 'on'): outstate = True
        if (state == 'off'): outstate = False
        if output in avr.outputs:
            print("Setting receiver output {0} to {1}".format(output, state))
            avr.enable_output(output, outstate)
        else:
            print(("That's not a valid output. Run `rxvc outputs' to"
                   "get a list of them."))
    else:
        click.echo(
            click.style("State must be on or off", fg='red')
        )

@cli.command(context_settings=CTX_SETTINGS)
@click.pass_context
def outputs(ctx):
    """List valid output names for this receiver.

    These are names that can also be passed to the output command
    when using it to set an output to a state.

    """
    avr = ctx.obj['avr']
    for output in sorted(ctx.obj['avr'].outputs.items()):
        print('* {0}: {1}'.format(output[0], output[1]))


# This command a little inconsistent with the input command in that
# setting the volume requires you pass an option rather than an
# argument. This is a limitation imposed by click. While with an
# option with the float type we can pass a negative number in,
# if we do this with an argument it tries to parse it as an option.
@cli.command(context_settings=CTX_SETTINGS)
@click.option('-v', '--vol', type=click.FLOAT, required=False)
@click.pass_context
def volume(ctx, vol):
    """Show the current receiver volume level, or set it with the
    -v/--vol option.

    """
    avr = ctx.obj['avr']
    if vol:
        if float(vol) < 0:
            try:
                avr.volume = vol
                click.echo(avr.volume)
            except ResponseException as e:
                if "Volume" in str(e):
                    msg = "Volume must be specified in -0.5 increments."
                    err = click.style(msg, fg='red')
                    click.echo(err, err=True)
        else:
            print("Volume must be specified as a negative float in "
                   "steps of 0.5.")
    else:
        click.echo(avr.volume)

# This command controls the mute function of the receiver and returns
# the current state if no argument is provided.
@cli.command(context_settings=CTX_SETTINGS)
@click.argument('mute', required=False)
@click.pass_context
def mute(ctx, mute):
    """Mute the audio output or return the status. If an argument is
    passed it should be 'on' or 'off', otherwise the current status
    is returned.

    """
    avr = ctx.obj['avr']
    status = ctx.obj['avr'].basic_status
    if mute:
        mute = mute.lower()
        try:
            avr.mute = mute == 'on'
            click.echo(mute)
        except ResponseException as e:
            if "Mute" in str(e):
                msg = "Mute command failed."
                err = click.style(msg, fg='red')
                click.echo(err, err=True)
    else:
        print(("Muted: {muted}").format(
                   muted=status.mute))


@cli.command(context_settings=CTX_SETTINGS)
@click.argument('state', required=False)
@click.pass_context
def power(ctx, state):
    """Power the receiver on or off. If an argument is passed it
    should be 'on' or 'off', otherwise just print the current
    power state.

    Note that RX-V receivers have a Network Standby setting that
    allows you to turn it on over the wire when the receiver is
    off, but by default this is not enabled. Make sure you turn
    that on!

    """
    avr = ctx.obj['avr']
    if state:
        state = state.lower()
        if state in ['on', 'off']:
            try:
                avr.on = state == 'on'
                click.echo("Turned the receiver {}".format(state))
            except:
                msg = (
                    "Something went wrong. Make sure the Network "
                    "Standby setting of your receiver is on."
                )
                click.echo(click.style(msg, fg='red'))
        else:
            click.echo(
                click.style("State must be on or off", fg='red')
            )
    else:
        state = 'on' if avr.on else 'off'
        click.echo("Power state is {}".format(state))


@cli.command(context_settings=CTX_SETTINGS)
@click.argument("sp", required=False)
@click.pass_context
def sp(ctx, sp):
    """See the current receiver surround program or set it if
    passed an argument that is a valid input for the receiver.
    Note that if it has spaces in it, you should wrap the whole
    argument in quotes.

    """
    avr = ctx.obj['avr']
    if sp:
        if sp in avr.surround_programs():
            print("Setting receiver surround program to {}".format(sp))
            avr.surround_program = sp
        else:
            print(("That's not a valid surround program. Run `rxvc sps'"
                   "to get a list of them."))
    else:
        print(avr.surround_program)


@cli.command(context_settings=CTX_SETTINGS)
@click.pass_context
def sps(ctx):
    """List valid surround program names for this receiver.

    These are names that can also be passed to the sp command
    when using it to select a surround program.

    """
    print("Valid surround programs for this receiver are:")
    for sp in sorted(ctx.obj['avr'].surround_programs()):
        print('* ', sp)


@cli.command(context_settings=CTX_SETTINGS)
@click.argument("zone", required=False)
@click.pass_context
def zone(ctx, zone):
    """See the current receiver zone or set it if passed an
    argument that is a valid zone for the receiver. Note that
    if it has spaces in it, you should wrap the whole
    argument in quotes.

    """
    avr = ctx.obj['avr']
    if zone:
        if zone in avr.zones():
            print("Setting receiver zone to {}".format(zone))
            avr.zone = zone
        else:
            print(("That's not a valid zone. Run `rxvc zones'"
                   "to get a list of them."))
    else:
        print(avr.zone)


@cli.command(context_settings=CTX_SETTINGS)
@click.pass_context
def zones(ctx):
    """List configured zone names for this receiver.

    """
    print("Configured zones for this receiver are:")
    for zone in sorted(ctx.obj['avr'].zones()):
        print('* ', zone)


@cli.command(context_settings=CTX_SETTINGS)
@click.argument("scene", required=False)
@click.pass_context
def scene(ctx, scene):
    """See the current receiver scene or set it if passed an argument
    that is a valid input for the receiver. Note that if it has spaces
    in it, you should wrap the whole argument in quotes.

    """
    avr = ctx.obj['avr']
    if scene:
        if scene in avr.scenes():
            print("Setting receiver scene to {}".format(scene))
            avr.scene = scene
        else:
            print(("That's not a valid scene. Run `rxvc scenes'"
                   "to get a list of them."))
    else:
        print(avr.scene)


@cli.command(context_settings=CTX_SETTINGS)
@click.pass_context
def scenes(ctx):
    """List valid scene names for this receiver.

    These are scenes that can also be passed to the scene command
    when using it to select a scene.

    """
    print("Valid scenes for this receiver are:")
    for scene in sorted(ctx.obj['avr'].scenes()):
        print('* ', scene)


@cli.command(context_settings=CTX_SETTINGS)
@click.option('-v', '--vol', type=click.FLOAT, required=False)
@click.argument('delay', type=click.FLOAT, required=False)
@click.pass_context
def fade(ctx, vol, delay=0.5):
    """Fade to a given volume with an optional delay between
    increments. The delay can be specified in seconds.

    """
    avr = ctx.obj['avr']
    if vol and (float(vol) < 0):
        try:
            print("Fading receiver volume to {0} with delay of {1} seconds".format(vol, delay))
            avr.volume_fade(int(vol), float(delay))
        except ResponseException as e:
            print(e)
            if "Volume" in str(e):
                msg = "Volume must be specified in -0.5 increments."
                err = click.style(msg, fg='red')
                click.echo(err, err=True)
    else:
        print("Volume must be specified as a negative float in "
               "steps of 0.5. Optionally, a delay can be "
               "specified in seconds.")


# Volume inc/dev convenience commands.

def _adjust_volume(avr, points, operation):
    """Adjust volume up or down by multiplying points by 0.5 and
    either subtracting from (decrease) or adding to (increase) the
    current volume level, printing an out of range (best guess) if
    the receiver complains about the new level.

    The last argument, operation, should be either operator.add or
    operator.sub.

    """
    current_vol = avr.volume
    new_vol = operation(current_vol, (points * 0.5))

    try:
        avr.volume = new_vol
        click.echo(new_vol)
    except ResponseException:
        click.echo(
            click.style("New volume must be out of range.",
                        fg='red')
        )


@cli.command(context_settings=CTX_SETTINGS)
@click.argument('points',
                type=click.INT,
                default=2,
                required=False)
@click.pass_context
def up(ctx, points):
    """Turn up the receiver volume in 0.5 increments. If no
    argument is passed, the argument defaults to 2 which is
    multiplied by 0.5 (the receiver's accepted increments)
    and added to current volume. If the argument is passed,
    you can control the number of increments.

    """
    avr = ctx.obj['avr']
    _adjust_volume(avr, points, operator.add)


@cli.command(context_settings=CTX_SETTINGS)
@click.argument('points',
                type=click.INT,
                default=2,
                required=False)
@click.pass_context
def down(ctx, points):
    """Turn down the receiver volume in 0.5 increments. If no
    argument is passed, the argument defaults to 2 which is
    multiplied by 0.5 (the receiver's accepted increments)
    and subtracted to current volume. If the argument is passed,
    you can control the number of increments.

    """
    avr = ctx.obj['avr']
    _adjust_volume(avr, points, operator.sub)


@cli.command(context_settings=CTX_SETTINGS)
@click.argument("command", required=False)
@click.pass_context
def playback(ctx, command):
    """See the current receiver playback status or pass a command to it.

    """
    if not ctx.obj['avr'].is_playback_supported():
        print("Playback controls are not available for the active input.")
        return

    avr = ctx.obj['avr']
    if command:
        if command in [ 'play', 'stop', 'pause', 'next', 'previous' ]:
            print("Sending command {} to receiver".format(command))
            if command == 'play': avr.play()
            if command == 'stop': avr.stop()
            if command == 'pause': avr.pause()
            if command == 'next': avr.next()
            if command == 'previous': avr.previous()
        else:
            print(("That's not a valid playback control command. Valid commands"
                   "include 'play', 'stop', 'pause', 'next' and 'previous'."))
    else:
        status = ctx.obj['avr'].play_status()
        print(("\nPlaying: {playing}\n"
               "Artist: {artist}\n"
               "Album: {album}\n"
               "Track: {song}\n"
               "Station: {station}\n").format(
                   playing=status.playing,
                   artist=status.artist,
                   album=status.album,
                   song=status.song,
                   station=status.station))

@cli.command(context_settings=CTX_SETTINGS)
@click.argument("command", required=False)
@click.pass_context
def menu(ctx, command):
    """See the current receiver menu status or operate it.

    """
    if not ctx.obj['avr'].menu_status().ready:
        print("Menu is currently not available.")
        return

    avr = ctx.obj['avr']
    if command:
        if command in [ 'up', 'down', 'left', 'right', 'select', 'return' ]:
            print("Sending menu command {} to receiver".format(command))
            if command == 'up': avr.menu_up()
            if command == 'down': avr.menu_down()
            if command == 'left': avr.menu_left()
            if command == 'right': avr.menu_right()
            if command == 'select': avr.menu_sel()
            if command == 'return': avr.menu_return()
        else:
            print(("That's not a valid menu control command. Valid commands "
                   "include 'up', 'down', 'left', 'right', 'select' and 'return'."))
            return

    status = ctx.obj['avr'].menu_status()
    print(("\nReady: {ready}\n"
           "Layer: {layer}\n"
           "Name: {name}\n\n"
           "Total lines: {max_line}\n").format(
               ready=status.ready,
               layer=status.layer,
               name=status.name,
               current_line=status.current_line,
               max_line=status.max_line))

    # print lines as displayed in the web interface
    for item in sorted(status.current_list.items()):
        print("*  {}".format(item[1]))
