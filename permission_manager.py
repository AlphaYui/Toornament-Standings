from persistent_json import JSONStorage

import discord
from discord.ext import commands

class PermissionManager:

    def __init__(self):
        self.__roles = JSONStorage("roles.json")

    def add_role(self, role: discord.Role):
        role_info = {
            "guild": role.guild.id,
            "role": role.id
        }
        self.__roles.content += [role_info]
        self.__roles.save()

    def remove_role(self, role: discord.Role):

        roles = []

        for perm_role in self.__roles.content:
            if not perm_role["guild"] == role.guild.id or not perm_role["role"] == role.id:
                roles += [perm_role]

        self.__roles.content = roles
        self.__roles.save()

    def has_perms(self, ctx: commands.Context):

        if ctx.author.permissions_in(ctx.channel).administrator:
            return True

        for member_role in ctx.author.roles:
            for perm_role in self.__roles.content:
                if member_role.guild.id == perm_role["guild"] and member_role.id == perm_role["role"]:
                    return True
        return False