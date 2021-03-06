###THIS PROGRAM USES RIOT API, OP.GG Weblinks and LolWatcher module for python.
### STUFF TO DO LATER: 

#  Add images? More champions stats? Improve formatting.

import requests
from riotwatcher import LolWatcher, ApiError
from configparser import ConfigParser
import discord
from discord.ext import commands, tasks
from datetime import datetime,timedelta
from bs4 import BeautifulSoup

#Read tokens/keys from config
leaguebot_config = ConfigParser()
leaguebot_config.read('config.txt')

discord_token = leaguebot_config['TOKENS']['DISCORD_TOKEN']
api_key = leaguebot_config['TOKENS']['API_KEY'] #REGISTERED!

watcher = LolWatcher(api_key)

all_champs = requests.get('http://ddragon.leagueoflegends.com/cdn/11.9.1/data/en_US/champion.json')
all_champs_dict = all_champs.json()

#get all champion info, compare it given list of id's and return name and id
def get_champion_names(list_champ_ids):
    """Gets champion names based on ID

    Args:
      list_champ_ids: list of champion IDs

    Return:
      List: list of lists containing champion name and id 
    """
    champion_names = []
    all_champs = requests.get('http://ddragon.leagueoflegends.com/cdn/11.9.1/data/en_US/champion.json')
    all_champs_dict = all_champs.json()
    for i in all_champs_dict['data']:
        if int(all_champs_dict['data'][i]['key']) in list_champ_ids:
            champion_names.append([all_champs_dict['data'][i]['id'], all_champs_dict['data'][i]['key']])

    return champion_names

#get champion info on top 5 champs by mastery score 
def get_champions(name: str, region: str='euw1'):
    """Get summoner champion data from API

    Args:
      name: str, summoner name to search
      region: str, server of the searched summoner. Defaults to Europe West/euw1

    Return:
      dict: info on top 5 champions of given user 
    """ 
    me = watcher.summoner.by_name(region, name)
    champions = watcher.champion_mastery.by_summoner(region, me['id'])
    
    return champions[0:5]

def get_champion_stats(name, region='euw1'):
    """Main function for champion mastery command, calls get_champions and get_champion_names
       and formats strings for the bot to send out.

    Args:
      name: summonername
      region: region/server name 
    
    Return:
      list: of formatted strings containing champion mastery data for the searched user.
    """
    user_champions = get_champions(name, region)
    user_champion_ids = []

    for i in user_champions:
        user_champion_ids.append(i['championId'])

    champion_names = get_champion_names(user_champion_ids)

    final_strings = []
    for user in user_champions:
        for name in champion_names:
            if int(user['championId']) == int(name[1]):
                final_strings.append([name[0], user['championPoints'], user['championLevel']])

    return final_strings

def get_ranked(name: str, region: str='euw1'):
    """Fetches ranked stats from the API
   
    Args:
      name: summonername searched by 
      region: name of region/server

    Return:
      tuple: ranked stats of user(0), user information(1)
    """
    me = watcher.summoner.by_name(region, name)
    ranked = watcher.league.by_summoner(region, me['id'])
    return ranked, me
    
def return_stats(x: list):
    """Formats ranked stats 

    Args:
      list: list of dicts containing ranked stat information called from the API 

    Return:
      list: containing formatted strings of name, que, rank, wins, losses of an user
    """
    winloss = x[0]['wins'] / (x[0]['wins'] + x[0]['losses']) * 100
    quetype = x[0]['queueType'].split('_')[1]
    name = x[0]['summonerName']
    if quetype == 'SOLO':
        que = 'Ranked Solo'
    if quetype == 'FLEX':
        que = 'Ranked Flex'
    rank = (f"{x[0]['tier']} {x[0]['rank']} {x[0]['leaguePoints']} LP")
    wins = x[0]['wins']
    losses = x[0]['losses']
    wr = (f"{winloss:.2f}")
       
    if len(x) > 1:
        solo_winloss = x[1]['wins'] / (x[1]['wins'] + x[1]['losses']) * 100
        solo_que = quetype = x[1]['queueType'].split('_')[1]
        if quetype == 'SOLO':
            solo_que = "Ranked Solo"
        solo_rank = (f"{x[1]['tier']} {x[1]['rank']} {x[1]['leaguePoints']} LP")
        solo_wins = x[1]['wins']
        solo_losses = x[1]['losses']
        solo_wr = (f"{solo_winloss:.2f}")

        return [name,que,rank,wins,losses,wr,solo_que,solo_rank,solo_wins,solo_losses,solo_wr]

    return [name,que,rank,wins,losses,wr]

def get_url(server: str):
    """Formats url based on given server

    Args:
      server: str, abbreviation of server 

    Return:
        str: op.gg url with correct server 
    """
    if server == 'euw':
        return 'https://euw.op.gg/summoner/userName='
    elif server == 'na':
        return 'https://na.op.gg/summoner/userName='
    elif server == 'eune':
        return 'https://eune.op.gg/summoner/userName='
    elif server == 'kr':
        return 'https://op.gg/summoner/userName='
    return None

def sort_summoner_name(name, name2, name3):
    """Adds spacebar formatting for names
    """
    if name2 == "":
        return name
    else:
        concat_name = name + "%20" + name2
        if name3 != "":
            concat_name += "%20" + name3
        return concat_name
    
def get_new_patch_notes():
    """Fetches new patch notes from Riot.

    Return:
        str: full URL to patch notes
    """ 
    a = requests.get("https://www.leagueoflegends.com/en-us/news/tags/patch-notes/")
    soup = BeautifulSoup(a.content, "html.parser")
    a_tags = soup.find("a")
    
    return "https://leagueoflegends.com" + a_tags["href"]

def save_patch_notes(patch):
    """Saves patch notes to a local file, used in comparing patch notes in automatic messaging.
    """
    with open("latest_patch.txt" , "w") as file_1:
        file_1.write(patch + "\n")
        file_1.close()

def compare_patch( teststring: str="none" ):
    """Fetch and compare latest patch notes to existing (local save) ones

    Return:
        Boolean: true if fetch is newer than saved
        String: full URL to new notes
    """
    latest = get_new_patch_notes()
    with open("latest_patch.txt" , "r") as file_1:
        saved =  file_1.read().strip("\n")  

    return latest != saved, latest      

#bot init, some datetime shenanigans
bot = commands.Bot(command_prefix='!')
year = datetime.now().strftime("%Y")
year_X = (datetime.now()+timedelta(days=365)).strftime("%Y")

#ranked stats for searched user
@bot.command(name='ranked')
async def lol_stats(ctx, server='euw', name="", name2="", name3=""):
    try:
        if server == "eune":
            server_full = "eun1"
        elif server != 'kr':
            server_full = server + '1'
        else: 
            server_full = server

        name = sort_summoner_name(name, name2, name3)
        user_url = get_url(server)
        user_url_full = user_url + name
        stat_base = get_ranked(name, server_full)
        stat_format = return_stats(sorted(stat_base[0], key=lambda x: x['queueType']))

        #message 
        embed = discord.Embed(
        title= f"OP.GG",
            url=user_url_full    
        )
        embed.add_field(name=f'League of legends {year}', value=f'Season {int(year) - 2010}')
        embed.add_field(name='Summoner', value=f"{stat_format[0]} (lvl {stat_base[1]['summonerLevel']})", inline=False)
        embed.add_field(name='------------------------', value='------------------------', inline=False)
        embed.add_field(name='Queue', value=stat_format[1], inline=False )
        embed.add_field(name='Rank', value=stat_format[2], inline=False )
        embed.add_field(name='Wins', value=stat_format[3], inline=False )
        embed.add_field(name='Losses', value=stat_format[4], inline=False )
        embed.add_field(name='Winrate', value=f"{stat_format[5]}%\n", inline=False )
        
        if len(stat_format) > 6:
            embed.add_field(name='------------------------', value='------------------------', inline=False)
            embed.add_field(name='Queue', value=stat_format[6], inline=False )
            embed.add_field(name='Rank', value=stat_format[7], inline=False )
            embed.add_field(name='Wins', value=stat_format[8], inline=False )
            embed.add_field(name='Losses', value=stat_format[9], inline=False )
            embed.add_field(name='Winrate', value=f"{stat_format[10]}%", inline=False )
        
        if stat_format[0] == 'DontPlayThisGame':
            embed.add_field(name='NOOB SINGED PLAYER', value='XDXDXDXDXD', inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        error_message = discord.Embed(

        )
        error_message.add_field(name='Something went wrong!', value="Check that your command is typed correctly.", inline=False)
        error_message.add_field(name='Not ranked? :/', value="This message is displayed with correct parameters if the user\nhas not completed ranked placement games in the current season!", inline=False)
        error_message.add_field(name='!command', value='Display bot commands and other information', inline=False)
        print(e)

        await ctx.send(embed=error_message)
        

#champion mastery for searched user
@bot.command(name='champs')
async def champions_mastery(ctx, server='euw', name="",name2="", name3=""):
    try:
        if server == "eune":
            server_full = "eun1"
        elif server != 'kr':
            server_full = server + '1'
        else: 
            server_full = server

        name = sort_summoner_name(name, name2, name3)
        user_champs = get_champion_stats(name, server_full)
        embed = discord.Embed(
        title= "Champion Mastery"       
        )
        
        embed.add_field(name=f'{user_champs[0][0]}', value=f"{user_champs[0][1]} points (lvl {user_champs[0][2]})", inline=False )
        embed.add_field(name=f'{user_champs[1][0]}', value=f"{user_champs[1][1]} points (lvl {user_champs[1][2]})", inline=False )
        embed.add_field(name=f'{user_champs[2][0]}', value=f"{user_champs[2][1]} points (lvl {user_champs[2][2]})", inline=False )
        embed.add_field(name=f'{user_champs[3][0]}', value=f"{user_champs[3][1]} points (lvl {user_champs[3][2]})", inline=False )
        embed.add_field(name=f'{user_champs[4][0]}', value=f"{user_champs[4][1]} points (lvl {user_champs[4][2]})", inline=False )
        
        await ctx.send(embed=embed)

    except Exception as e:
        error_message = discord.Embed(
        )
        error_message.add_field(name='Something went wrong!', value="Check that your command is typed correctly.")
        error_message.add_field(name='!command', value='Display bot commands and other information', inline=False)
        
        await ctx.send(embed=error_message)

@bot.command(name = 'patch')
async def patch_notes(ctx):
    try:
        patch_notes = get_new_patch_notes()
        await ctx.send(patch_notes)
    except Exception as e:
        await ctx.send("No patch notes found :O\nPlease try again later!")

#help/info command!
@bot.command(name = 'command')
async def help_print(ctx):
    message = discord.Embed(
        title = 'Commands'
    )
    message.add_field(name='!ranked', value='Type !ranked server summonername to get ranked stats!', inline=False)
    message.add_field(name='!champs', value='Type !champs server summonername to get 5 most played champs!', inline=False)
    message.add_field(name='!patch', value='Type !patch to get the latest patch notes (link)', inline=False)
    message.add_field(name='Supported servers', value='North America = na\nEurope West = euw\nEurope Nordic/East = eune\nKorea = kr', inline=False)
    
    await ctx.send(embed=message)

#task for automated patch posting 
#runs every 6 hours checks if there is a new patch, if yes send a message containing a link to the patch notes
#atm only works for one specific guild!
@tasks.loop(hours=6)
async def automated_patch_notes():
    is_new_patch, latest_patch = compare_patch()

    if is_new_patch:
        channel = discord.utils.get(bot.get_all_channels())
        if channel.name == "moti":
            await channel.send("League of legends new patch notes!\n" + latest_patch)
        save_patch_notes(latest_patch)  
    else:
        return
   
#bot waits for the loops
@automated_patch_notes.before_loop
async def before():
    await bot.wait_until_ready() 

automated_patch_notes.start()

if __name__ == '__main__':
    print("Bot Connected!")
    bot.run(discord_token) 

    print("Bot loggin off...")











