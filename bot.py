import discord
from discord.ext import commands

from toornament import ToornamentAPI
from embed_generator import EmbedGenerator
from permission_manager import PermissionManager

# Initializes Toornament API.
too = ToornamentAPI("auth/toornament.json")

# Initializes Discord bot.
with open("auth/discord.token", 'r') as token_file:
    token = token_file.read().strip(' \n')


# Initializes Embed generator for rankings&fixtures
embed_gen = EmbedGenerator()

# Initializes permission manager.
perms = PermissionManager()

# Initializing bot.
bot = commands.Bot(command_prefix = '+')

@bot.command()
async def ping(ctx):
    "Simple ping to check if the bot is online."

    if perms.has_perms(ctx):
        await ctx.send('pong')


@bot.command()
async def addgroup(ctx: commands.Context, tournament_id, group_name: str, alias: str, colour, logo_url):
    """Adds a Toornament group to the bot. 
    
    Parameters:
    #1 - Tournament ID: Unique ID of the tournament on Toornament.com.
    #2 - Group name:    Name of the group on Toornament.com (e.g. "Division 2.2").
    #3 - Alias:         An alias to refer to the group more easily in the future (e.g. "D2.2").
    #4 - Colour:        Colour of the embed as a hex code (e.g. "#FF0000" for red).
    #5 - Logo URL:      URL of the group icon (e.g. "https://imgur.com/EBv6Vza.png")

    !addgroup 4240827061098184704 "The Vortex" Vortex #00AAFF https://imgur.com/mj8KanR.png
    """

    # Checks if the user has permission to use this command.
    if not perms.has_perms(ctx):
        await ctx.send("Permission denied")
        return

    # Finds the group on Toornament.com.
    group = too.get_group_info(tournament_id, group_name)


    # Checks if the group exists.
    if group is None:
        await ctx.send(f"Couldn't find group '{group_name}' for tournament '{tournament_id}'.")
        return

    # Adds the group to the bot.
    embed_gen.add_stage(alias, group, logo_url, colour)

    # Gives feedback to the user.
    stage_id = group["stage_id"]
    group_id = group["id"]
    await ctx.send(f"Added group '{group_name}' with ID '{group_id}' for stage '{stage_id}'!")


@bot.command()
async def removegroup(ctx: commands.Context, group_name: str):
    """Removes a Toornament group from the bot.

    Parameters:
    #1 - Group name: Name or alias of the group to be removed.

    Example: !removegroup Vortex
    """

    # Checks if the user has permission to use this command.
    if not perms.has_perms(ctx):
        await ctx.send("Permission denied")
        return

    # Removes the group from the bot.
    embed_gen.remove_stage(group_name)

    # Gives feedback to the user.
    await ctx.send(f"Removed group '{group_name}' from the bot.")


@bot.command()
async def group(ctx: commands.Context, group_name: str, week):
    """Posts the ranking and fixtures of a single group in the same channel.

    Parameters:
    #1 - Group name: Name or alias of the group to be posted about.
    #2 - Week:       Number of the week for which the fixtures should be posted.

    Example: !group Vortex 3
    """

    # Checks if the user has permission to use this command.
    if not perms.has_perms(ctx):
        await ctx.send("Permission denied")
        return

    # Generates the embed for this group in the given week.
    embed = embed_gen.generate_embed(ctx, too, group_name, week)

    # Posts the embed to the channel.
    await ctx.send(embed = embed)


@bot.command()
async def addsequence(ctx: commands.Context, seq_name: str, seq_groups: str):
    """Adds a sequence of multiple groups to be posted at once in a given order.

    Parameters:
    #1 - Sequence name: Name by which the sequence is later referenced in other commands.
    #2 - Groups: A comma separated list of all groups in the sequence in the order they should be posted.

    Example: !addsequence ECC8 CC1,CC2,Vortex
    """

    # Checks if the user has permission to use this command.
    if not perms.has_perms(ctx):
        await ctx.send("Permission denied")
        return

    # Separates the list of groups by commas.
    groups = seq_groups.split(',')

    # Adds the sequence to the bot.
    embed_gen.add_sequence(seq_name, groups)

    # Feedback to the user.
    group_str = '\n'.join(groups)
    await ctx.send(f"Created sequence '{seq_name}' containing the following groups:\n{group_str}")


@bot.command()
async def removesequence(ctx: commands.Context, seq_name: str):
    """Removes a sequence from the bot.

    Parameters:
    #1 - Sequence name: Name of the sequence to remove.
    """

    # Checks if the user has permission to use this command.
    if not perms.has_perms(ctx):
        await ctx.send("Permission denied")
        return

    # Removes the sequence from the bot.
    embed_gen.remove_sequence(seq_name)

    # Feedback to the user.
    await ctx.send(f"Removed sequence '{seq_name}'.")


@bot.command()
async def sequence(ctx: commands.Context, seq_name: str, week):
    """Posts ranking and fixtures for each group in a given sequence.

    Parameters:
    #1 - Sequence name: Name of the sequence to post in the channel.
    #2 - Week:          Week for which the fixtures should be posted.
    """

    # Checks if the user has permission to use this command.
    if not perms.has_perms(ctx):
        await ctx.send("Permission denied")
        return

    # Generates a ranking&fixture embed for every group in the sequence.
    embeds = embed_gen.generate_sequence_embeds(ctx, too, seq_name, week)

    # Posts all the embeds.
    for embed in embeds:
        await ctx.send(embed = embed)


@bot.command()
async def addrole(ctx: commands.Context, role: discord.Role):
    """Adds a role that can use commands of this bot.

    Parameters:
    #1 - Role: ID or mention of the role to be added.
    """

    # Checks if the user has admin privileges.
    if not ctx.author.permissions_in(ctx.channel).administrator:
        await ctx.send("Permission denied")
        return

    # Checks if the added role belongs to the server (so that you can't edit privileges for other servers).
    if not role.guild.id == ctx.guild.id:
        await ctx.send("Permission denied")
        return

    # Adds role to the permission list.
    perms.add_role(role)

    await ctx.send(f"Users from {role.mention} now have permissions for this bot.")
        
@bot.command()
async def removerole(ctx: commands.Context, role: discord.Role):
    """Removes a role's ability to use commands of this bot.

    Parameters:
    #1 - Role: ID or mention of the role to be removed.
    """
    
    # Checks if the user has admin privileges.
    if not ctx.author.permissions_in(ctx.channel).administrator:
        await ctx.send("Permission denied")
        return

    # Checks if the added role belongs to the server (so that you can't edit privileges for other servers).
    if not role.guild.id == ctx.guild.id:
        await ctx.send("Permission denied")
        return
    
    # Removes role from the permission list.
    perms.remove_role(role)
    

print("Starting bot...")
bot.run(token)