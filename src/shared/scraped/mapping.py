# -*- coding: utf-8 -*-

"""
Serenity License (Attribution-NonCommercial-ShareAlike 4.0 International)

You are free to:

  - Share: copy and redistribute the material in any medium or format.
  - Adapt: remix, transform, and build upon the material.

The licensor cannot revoke these freedoms as long as you follow the license
terms.

Under the following terms:

  - Attribution: You must give appropriate credit, provide a link to the
    license, and indicate if changes were made. You may do so in any reasonable
    manner, but not in any way that suggests the licensor endorses you or your
    use.
  
  - Non-Commercial: You may not use the material for commercial purposes.
  
  - Share Alike: If you remix, transform, or build upon the material, you must
    distribute your contributions under the same license as the original.
  
  - No Additional Restrictions: You may not apply legal terms or technological
    measures that legally restrict others from doing anything the license
    permits.

This is a human-readable summary of the Legal Code. The full license is available
at https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode
"""

__all__: tuple[str, ...] = ("check_owo_command",)


owo_commands: set[str] = {
    # battle folder
    "ab",
    "acceptbattle",
    "battle",
    "b",
    "fight",
    "battlesetting",
    "bs",
    "battlesettings",
    "crate",
    "weaponcrate",
    "wc",
    "db",
    "declinebattle",
    "pets",
    "pet",
    "rename",
    "team",
    "squad",
    "tm",
    "teams",
    "setteam",
    "squads",
    "useteams",
    "weapon",
    "w",
    "weapons",
    "wep",
    "weaponshard",
    "ws",
    "weaponshards",
    "dismantle",
    # economy folder
    "claim",
    "reward",
    "compensation",
    "cowoncy",
    "money",
    "currency",
    "cash",
    "credit",
    "balance",
    "daily",
    "give",
    "send",
    "quest",
    "q",
    # emotes folder
    "gif",
    "pic",
    # self emotes
    "blush",
    "cry",
    "dance",
    "lewd",
    "pout",
    "shrug",
    "sleepy",
    "smile",
    "smug",
    "thumbsup",
    "wag",
    "thinking",
    "triggered",
    "teehee",
    "deredere",
    "thonking",
    "scoff",
    "happy",
    "thumbs",
    "grin",
    # user emotes
    "cuddle",
    "hug",
    "kiss",
    "lick",
    "nom",
    "pat",
    "poke",
    "slap",
    "stare",
    "highfive",
    "bite",
    "greet",
    "punch",
    "handholding",
    "tickle",
    "kill",
    "hold",
    "pats",
    "wave",
    "boop",
    "snuggle",
    "fuck",
    "sex",
    # gamble folder
    "blackjack",
    "bj",
    "21",
    "coinflip",
    "cf",
    "coin",
    "flip",
    "drop",
    "pickup",
    "lottery",
    "bet",
    "lotto",
    "slots",
    "slot",
    "s",
    # memgen folder
    "communism",
    "communismcat",
    "distractedbf",
    "distracted",
    "drake",
    "eject",
    "amongus",
    "emergency",
    "emergencymeeting",
    "headpat",
    "isthisa",
    "slapcar",
    "slaproof",
    "spongebobchicken",
    "schicken",
    "tradeoffer",
    "waddle",
    # patreon folder
    "02kiss",
    "alastor",
    "angel",
    "agl",
    "army",
    "babyyoda",
    "boba",
    "bonk",
    "bomk",
    "bully",
    "bunny",
    "butterfly",
    "btf",
    "cake",
    "candycane",
    "catto",
    "shifu",
    "ufo",
    "chicken",
    "jester",
    "choose",
    "pick",
    "decide",
    "coffee",
    "java",
    "compliment",
    "bnice",
    "crown",
    "cupachicake",
    "cpc",
    "death",
    "destiny",
    "dtn",
    "devil",
    "dvl",
    "roll",
    "d20",
    "dish",
    "donut",
    "dragon",
    "dgn",
    "duwasvivu",
    "egg",
    "fate",
    "frogegg",
    "gauntlet",
    "genie",
    "goldenegg",
    "grim",
    "icecream",
    "king",
    "latte",
    "life",
    "lollipop",
    "love",
    "magic",
    "meshi",
    "milk",
    "mochi",
    "moon",
    "nier",
    "obw",
    "pika",
    "pikapika",
    "piku",
    "pizza",
    "poutine",
    "puppy",
    "pup",
    "queen",
    "rain",
    "rainbow",
    "raindrop",
    "rose",
    "bouquet",
    "rum",
    "run",
    "sakura",
    "sammy",
    "sharingan",
    "slime",
    "snake",
    "snowball",
    "bell",
    "strengthtest",
    "sun",
    "sunflower",
    "taco",
    "tarot",
    "tequila",
    "truthordare",
    "td",
    "turnip",
    "water",
    "wolf",
    "yinyang",
    "yy",
    "zodiackey",
    "zk",
    # collectibles folder
    "fear",
    "nommy",
    "bear",
    "ginseng",
    "grizzly",
    "smokeheart",
    "heart",
    "panda",
    "sonic",
    "teddy",
    "carlspider",
    "des",
    "flame",
    "flm",
    "penguin",
    "pgn",
    "star",
    "music",
    "msc",
    "corgi",
    "doggo",
    "saturn",
    "spider",
    "doll",
    "martini",
    # ranking folder
    "my",
    "me",
    "guild",
    "top",
    "rank",
    "ranking",
    "buy",
    "describe",
    "desc",
    "equip",
    "use",
    "inventory",
    "inv",
    "shop",
    "market",
    "trade",
    "tr",
    "gift",
    # social folder
    "acceptmarriage",
    "am",
    "cookie",
    "rep",
    "declinemarriage",
    "dm",
    "define",
    "discordplays",
    "twitchplays",
    "emulator",
    "divorce",
    "eightball",
    "8b",
    "ask",
    "8ball",
    "emoji",
    "enlarge",
    "jumbo",
    "level",
    "lvl",
    "levels",
    "xp",
    "propose",
    "marry",
    "marriage",
    "wife",
    "husband",
    "owo",
    "owoify",
    "ify",
    "pray",
    "curse",
    "profile",
    "ship",
    "combine",
    "translate",
    "listlang",
    "tl",
    "wallpaper",
    "wp",
    "wallpapers",
    "background",
    "backgrounds",
    # utils folder
    "announce",
    "changelog",
    "announcement",
    "announcements",
    "avatar",
    "user",
    "censor",
    "checklist",
    "task",
    "tasks",
    "cl",
    "color",
    "randcolor",
    "colour",
    "randcolour",
    "covid",
    "cv",
    "covid19",
    "coronavirus",
    "disable",
    "distorted",
    "dt",
    "enable",
    "guildlink",
    "help",
    "invite",
    "link",
    "math",
    "calc",
    "calculate",
    "patreon",
    "donate",
    "ping",
    "pong",
    "prefix",
    "rule",
    "rules",
    "shards",
    "shard",
    "stats",
    "stat",
    "info",
    "suggest",
    "survey",
    "uncensor",
    "vote",
    # zoo folder
    "autohunt",
    "huntbot",
    "hb",
    "hunt",
    "h",
    "catch",
    "lootbox",
    "lb",
    "owodex",
    "od",
    "dex",
    "d",
    "sacrifice",
    "essence",
    "butcher",
    "sac",
    "sc",
    "sell",
    "upgrade",
    "upg",
    "zoo",
    "z",
}


def check_owo_command(command: str) -> bool:
    return command in owo_commands
