from toornament import ToornamentAPI
from persistent_json import JSONStorage

import discord
from discord.ext import commands

class EmbedGenerator:

    def __init__(self):
        self.__stages = JSONStorage("data/stages.json")
        self.__sequences = JSONStorage("data/sequences.json")


    ### GENERATING THE FIXTURES ###

    def __get_emote_id(self, guild: discord.Guild, emote_name: str):
        """Returns the mention of an emote with a given name in a certain guild.

        Parameters:
        guild:      discord.Guild object of the server with the emote.
        emote_name: Name of the emote to search.
        """

        emote_name = emote_name.lower()

        for emoji in guild.emojis:
            if emoji.name.lower() == emote_name:
                return f"<:{emoji.name}:{emoji.id}>"
        
        return None

    def __team_name_to_emote_name(self, team_name: str):
        """Guesses the emote name of a given team.
        For this, whitespaces are removed and following letters are capitalized.

        Parameters:
        team_name: Name of the team to guess the emote for.
        """

        prev_whitespace = True
        emote_name = ""
        for char in team_name:
            if char == ' ':
                prev_whitespace = True
            elif prev_whitespace:
                emote_name += char.upper()
                prev_whitespace = False
            else:
                emote_name += char

        return emote_name

    def __find_emote_id(self, guild: discord.Guild, team_info: dict):
        """Finds the emote ID for a given team.
        First the given emote name is searched, secondly an emote name is guessed from the team name.

        Parameters:
        guild: discord.Guild object of the server with the emote.
        team_info: Dictionary describing the team.
        """

        # If an emote is given for the team: Tries to find the emote in the guild.
        if team_info["emote"] is not None:
            emote_id = self.__get_emote_id(guild, team_info["emote"])

            if emote_id is not None:
                return emote_id

        # If no emote was given, or the given one was invalid:
        # Guesses an alternative emote name based on the team name.
        guessed_emote = self.__team_name_to_emote_name(team_info["name"])

        # Tries to find the guessed emote.
        emote_id = self.__get_emote_id(guild, guessed_emote)

        # Returns grey question mark as a default is no emote is found for the team.
        if emote_id is None:
            return ":grey_question:"

        return emote_id

    def __apply_match_forfeit(self, team):
        "Changes the score of a team to 'W' if it didn't forfeit or 'FF' if it did."

        if team["forfeit"]:
            team["score"] = "FF"
        else:
            team["score"] = "W"


    def __get_match_info(self, match):
        "Extracts the most important info from a match."

        home_team = match["opponents"][0]
        away_team = match["opponents"][1]

        # Converts scores to W and FF if there was at least one forfeit
        if home_team["forfeit"] or away_team["forfeit"]:
            self.__apply_match_forfeit(home_team)
            self.__apply_match_forfeit(away_team)

        return {
            "status": match["status"],
            "home_team": {
                "name": home_team["participant"]["name"],
                "emote": home_team["participant"]["custom_fields"]["emote"],
                "short": home_team["participant"]["custom_fields"]["short_name"],
                "score": home_team["score"]
            },
            "away_team": {
                "name": away_team["participant"]["name"],
                "emote": away_team["participant"]["custom_fields"]["emote"],
                "short": away_team["participant"]["custom_fields"]["short_name"],
                "score": away_team["score"]
            }
        }

    def __get_match_string(self, guild: discord.Guild, match):
        "Generates text for a single match."

        home_team = match['home_team']
        away_team = match['away_team']

        home_emote = self.__find_emote_id(guild, home_team)
        away_emote = self.__find_emote_id(guild, away_team)

        if home_team["short"] is None:
            home_name = home_team["name"]
        else:
            home_name = home_team["short"]

        if away_team["short"] is None:
            away_name = away_team["name"]
        else:
            away_name = away_team["short"]

        home_str = f"{home_name} {home_emote}"
        away_str = f"{away_emote} {away_name}"

    
        if match["status"] == "pending":
            # If the match was not played yet, no result is added.
            return f"{home_str} vs {away_str}"
            
        else:
            # If the match has been completed or is ongoing, the result is added.
            result_str = f"{home_team['score']}-{away_team['score']}"
            return f"{home_str} {result_str} {away_str}"


    def __generate_fixture_text(self, guild: discord.Guild, matches):
        "Generates a text for all given fixtures."

        # Extracts needed information for all matches.
        matches = [self.__get_match_info(match) for match in matches]

        # Generates string for every match and joins them.
        match_str = [self.__get_match_string(guild, match) for match in matches]
        match_str = '\n'.join(match_str)

        return match_str


    def __str_to_colour(self, colour_code: str) -> discord.Colour:
        "Converts a colour hex code into a discord.Colour object."

        colour_code = colour_code.strip('#')
        r = int(colour_code[:2], 16)
        g = int(colour_code[2:4], 16)
        b = int(colour_code[4:], 16)
        return discord.Colour.from_rgb(r, g, b)


    ### GENERATING THE RANKING ###

    def __pad_dictionary(self, keys, dict_list):
        """Pads all given fields in each dictionary to match the size of the largest element.
        
        keys: List of dictionary keys whose values should be padded.
        dict_list: List of dictionaries to be padded.
        """

        paddings = {}

        # Gathers the maximum size of a value of the given field.
        for key in keys:
            field_lengths = [len(entry[key]) for entry in dict_list]
            paddings[key] = max(field_lengths)

        # Adds padding to every entry in the list.
        for entry in dict_list:
            for key in keys:
                # Gets size of the element for this element and target size.
                actual_size = len(entry[key])
                target_size = paddings[key]

                # Adds whitespaces to match the target size.
                padded_content = entry[key] + " " * (target_size - actual_size)

                # Updates the string in the dictionary.
                entry[key] = padded_content


    def __get_rank_info(self, team):
        "Returns all important information on a single team from a ranking and formats each element as string."

        rank = team['rank']

        if rank is None:
            rank = team['position']

        name = team["participant"]["custom_fields"]["short_name"]

        if name is None:
            name   = team['participant']['name']
            
        wins   = team['properties']['wins']
        losses = team['properties']['losses']
        diff   = team['properties']['score_difference']

        return {
            "rank": f"#{rank}",
            "name": name,
            "win_loss": f"{wins}-{losses}",
            "diff": f"{diff:+}"
        }


    def __get_ranking_str(self, team, keys, separator = ' | '):
        "Generates a ranking line for a single team."
        values = [team[key] for key in keys]
        return separator.join(values)


    def __generate_ranking_text(self, ranking):
        "Generates a text-based ranking table."

        # Extracts all needed info from the ranking
        ranking = [self.__get_rank_info(team) for team in ranking]

        # Pads all fields to have the same width for every team so that they line up in a table.
        keys = ["rank", "name", "win_loss", "diff"]
        self.__pad_dictionary(keys, ranking)

        # Generates a line in the ranking for every team.
        ranking_str = [self.__get_ranking_str(team, keys) for team in ranking]
        ranking_str = '\n'.join(ranking_str)

        return ranking_str



    ### STAGES ### 

    def add_stage(self, alias, group_info, logo_url, colour):

        stage_info = {
            "alias": alias.lower(),
            "group": group_info,
            "logo": logo_url,
            "colour": colour
        }

        self.__stages.content += [stage_info]
        self.__stages.save()

    def remove_stage(self, alias):

        stages = []

        for stage in self.__stages.content:
            if not stage["alias"] == alias and not stage["group"]["name"] == alias:
                stages += [stage]

        self.__stages.content = stages
        self.__stages.save()
        

    def get_stage(self, stage_name: str):

        stage_name = stage_name.lower()
        for stage in self.__stages.content:
            if stage["alias"] == stage_name or stage["group"]["name"] == stage_name:
                return stage
            
        return None



    def generate_embed(self, ctx: commands.Context, too: ToornamentAPI, stage_name: str, week):

        stage = self.get_stage(stage_name) # TODO: Handle if stage isn't found.
        group = stage["group"]

        tournament = too.get_tournament(group["tournament_id"])
        ranking = too.get_ranking(group["tournament_id"], group["stage_id"], group["id"])
        matches = too.get_matches(group["tournament_id"], group["stage_id"], group["id"], week)

        ranking_text = f"```{self.__generate_ranking_text(ranking)}```"
        matches_text = self.__generate_fixture_text(ctx.guild, matches)

        embed = discord.Embed(
            title = group["name"],
            type = "rich",
            url = f"https://www.toornament.com/en_GB/tournaments/{group['tournament_id']}/stages/{group['stage_id']}/groups/{group['id']}",
            colour = self.__str_to_colour(stage["colour"])
        )

        embed.set_thumbnail(url = stage["logo"])
        embed.set_footer(text = tournament["name"], icon_url = tournament["logo"]["logo_small"])

        embed.add_field(name = "Standings", value = ranking_text, inline = False)
        embed.add_field(name = f"Week {week}", value = matches_text, inline = False)

        return embed



    ### SEQUENCES ###

    def add_sequence(self, alias: str, stage_list: list):

        sequence_info = {
            "alias": alias.lower(),
            "groups": stage_list
        }

        self.__sequences.content += [sequence_info]
        self.__sequences.save()

    def remove_sequence(self, alias: str):

        sequences = []

        for sequence in self.__sequences.content:
            if not sequence["alias"] == alias:
                sequences += [sequence]

        self.__sequences.content = sequences
        self.__sequences.save()

    def get_sequence(self, sequence_name: str):

        sequence_name = sequence_name.lower()
        for sequence in self.__sequences.content:
            if sequence["alias"] == sequence_name:
                return sequence

        return None


    def generate_sequence_embeds(self, ctx: commands.Context, too: ToornamentAPI, sequence_name: str, week):

        sequence = self.get_sequence(sequence_name) # TODO: Handle if sequence isn't found
        embeds = [self.generate_embed(ctx, too, group_name, week) for group_name in sequence["groups"]]
        return embeds
