# Connect 4 Discord Bot
from discord.ext import commands
import asyncio
import datetime
import random
import math

class Game:
    def __init__(self, grid_size):
        self.pieces = {}
        self.grid_size = grid_size

    def play_move(self, player, column):
        if column < 0 or column > self.grid_size[0]:
            print("Invalid column")
        
        # Search from top for existing piece, if none then place at y = 0
        placed = False
        for y in range(self.grid_size[1]):
            if (column, y) not in self.pieces:
                self.pieces[(column, y)] = player
                placed = True
                break

        return placed

    def get_board(self):
        # Create and populate board
        board = [[u"\U00002b1b" for _ in range(self.grid_size[0])] for _ in range(self.grid_size[1])]
        for xy in self.pieces.keys():
            board[self.grid_size[1] - xy[1] - 1][xy[0]] = str(self.pieces[xy])
        return '\n'.join([' '.join(elem) for elem in board])

    def check_win(self):
        # For each point check 4 to the right up and diagional
        for xy in self.pieces.keys():
            user = self.pieces[xy]
            # Horizonal and Vertical displacements
            h_displacements = [(xy[0] + 1, xy[1]), (xy[0] + 2, xy[1]), (xy[0] + 3, xy[1])]
            v_displacements = [(xy[0], xy[1] + 1), (xy[0], xy[1] + 2), (xy[0], xy[1] + 3)]
            # Diagonal right and diagonal left displacements
            dl_displacements = [(xy[0] + 1, xy[1] + 1), (xy[0] + 2, xy[1] + 2), (xy[0] + 3, xy[1] + 3)]
            dr_displacements = [(xy[0] + 1, xy[1] - 1), (xy[0] + 2, xy[1] - 2), (xy[0] + 3, xy[1] - 3)]

            if all([True if (displacment in self.pieces and self.pieces[displacment] == user) else False for displacment in h_displacements]):
                return user
            elif all([True if (displacment in self.pieces and self.pieces[displacment] == user) else False for displacment in v_displacements]):
                return user
            elif all([True if (displacment in self.pieces and self.pieces[displacment] == user) else False for displacment in dl_displacements]):
                return user
            elif all([True if (displacment in self.pieces and self.pieces[displacment] == user) else False for displacment in dr_displacements]):
                return user
        return -1

def can_cast_int(string):
    try:
        return isinstance(int(string), int)
    except ValueError:
        return False

# Setup Bot
client = commands.Bot(command_prefix='!')
with open("token", "r") as file:
  token = file.read()

@client.event
async def on_message(message):
    if message.content[:5] == "!game":
        content = message.content.split(" ")
        if len(content) < 3:
            if content[0] == "!game":
                await message.reply("Connect 4 Game\nTo use type `!game (board size) (tag other players)`\n\nHere is an example that starts a game with board size 8 by 6 with the user tagged:\n!game 8x6 <@!714565886119247923>")
            else:
                await message.reply("There is an invalid amount of parameters")
            return

        # Check gridsize
        grid_size = content[1].lower().split("x")
        if len(grid_size) != 2 or not (can_cast_int(grid_size[0]) and can_cast_int(grid_size[1])) or (int(grid_size[0]) < 1 or int(grid_size[0]) > 10) or (int(grid_size[1]) < 1 or int(grid_size[1]) > 10):
            await message.reply("The grid size needs to be two numbers seperated by an x with a maximum size of 10x10:\n`8x6`")
            return
        grid_size = tuple([int(dim) for dim in grid_size])

        # Check players
        players = {mention for mention in message.mentions if mention.id != message.author.id}
        if len(players) < 1 or len(players) > 4:
            await message.reply("You must tag between 1 and 4 other people to play with")
            return
        players = random.sample(list(players) + [message.author], len(players) + 1)
        
        # Check the bot is not in the players
        if any([player.bot for player in players]):
            await message.reply("You cannot play a game with a bot")
            return
        
        # Verify that all players are there
        game_message = await message.channel.send(f"{message.author.mention} has started a game with {', '.join([player.mention for player in players])}, if you want to play please click the tick reaction within the next 2 minutes.\nThe game will start once everyone has reacted.")
        verify_message_time = datetime.datetime.now()
        await game_message.add_reaction(u"\u2705")

        # Check message for 2 minutes every 2 seconds
        game_should_start = False
        while datetime.datetime.now() < (verify_message_time + datetime.timedelta(seconds=60)):
            # Get updated stats and calculate if we should start or not
            game_message = await message.channel.fetch_message(game_message.id)
            user_reactions = [reaction.users() for reaction in game_message.reactions if reaction.emoji == u"\u2705"][0]
            user_reactions = [user async for user in user_reactions]
            if set(players) - set(user_reactions) == set():
                game_should_start = True
                break
            else:
                game_should_start = False
            await asyncio.sleep(2)        
        
        if not game_should_start:
            await game_message.edit("Some of the players did not react in time so the game has been cancelled")
            return
        
        # Choosing colours for the players, just use the colour at the index of the player in the player list
        colours = [u"\U0001f534", u"\U0001f7e0", u"\U0001f7e1", u"\U0001f7e2", u"\U0001f7e3", u"\U0001f7e4"]
        colours = random.sample(colours, len(colours))
        game_message_head = f"{chr(10).join([str(colours[i] + ' : ' + players[i].mention) for i in range(len(players))])}\n"

        # Attempt to remove all reactions and then add the number reactions
        await game_message.clear_reactions()
        
        # Controls are left arrow, down arrow and right arrow respectivly
        controls = [u"\U00002b05", u"\U00002b07", u"\U000027a1"]
        for control in controls:
            await game_message.add_reaction(control)

        # Now the game loop should start
        game = Game(grid_size)
        current_player_index = 0
        current_dropper_pos = grid_size[0]//2
        previous_drop_time = datetime.datetime.now()
        while (game_winner := game.check_win()) == -1:
            # Check the reactions and move the circle
            game_message = await message.channel.fetch_message(game_message.id)
            for reaction in game_message.reactions:
                if reaction.emoji not in controls:
                    await reaction.clear()
                    continue
                async for user in reaction.users():
                    if user in players:
                        index = players.index(user)
                        if index == current_player_index:
                            control_index = controls.index(reaction.emoji)
                            # Left Button
                            if control_index == 0:
                                current_dropper_pos -= 1
                            # Drop Button
                            elif control_index == 1:
                                if game.play_move(colours[current_player_index], current_dropper_pos):
                                    current_player_index += 1
                                    current_player_index %= len(players)
                                    current_dropper_pos = grid_size[0]//2
                                    previous_drop_time = datetime.datetime.now()
                            # Right button
                            elif control_index == 2:
                                current_dropper_pos += 1
                            current_dropper_pos %= grid_size[0]

                            await reaction.remove(user)
                        else:
                            await reaction.remove(user)
                    else:
                        if user != client.user:
                            await reaction.remove(user)

            # Get time left
            time_left = datetime.datetime.now() - previous_drop_time
            if time_left > datetime.timedelta(seconds=30):
                # Skip turn
                current_player_index += 1
                current_player_index %= len(players)
                current_dropper_pos = grid_size[0]//2
                previous_drop_time = datetime.datetime.now()
            time_left_string = f"You have {30 - math.floor(time_left.total_seconds()/5)*5} seconds left\n"

            # 'Redraw' the game (by editing the message)
            dropper = ' '.join(u"\U00002b1c"*current_dropper_pos + colours[current_player_index] + u"\U00002b1c"*(grid_size[0]-current_dropper_pos-1)) + "\n"
            new_game_message = str(game_message_head + dropper + time_left_string + game.get_board())
            if new_game_message != game_message.content:
                await game_message.edit(content=new_game_message)
        
        # Edit the message to include the winner, and remove all the reactions
        game_winner_index = colours.index(game_winner)
        win_message = game_message.content + f"\n\n{game_winner} {players[game_winner_index].mention} won the game!"
        await game_message.clear_reactions()
        await game_message.edit(content=win_message)



@client.event
async def on_ready():
  print("ready")

client.run(token)


