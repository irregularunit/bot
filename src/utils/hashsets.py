"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

import bisect

__all__: tuple[str, ...] = ("check_owo_command",)

owo_commands: tuple[str, ...] = (
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
    # https:#github.com/ChristopherBThai/Discord-OwO-Bot/blob/master/src/data/emotes.json
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
    # https:#github.com/ChristopherBThai/Discord-OwO-Bot/blob/335ade88e1f452367d9cbf4cc3d2eff243e8708b/src/commands/commandList/patreon/utils/collectibles.json
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
)

sorted_owo_commands = sorted(owo_commands)


def check_owo_command(command: str) -> bool:
    index: int = bisect.bisect_left(sorted_owo_commands, command.lower())
    return index != len(sorted_owo_commands) and sorted_owo_commands[index] == command


if __name__ == "__main__":
    import timeit

    commands: list[str] = ["owo", "uwu", "what", "hunt", "huntbot", "PRAY", "pray X"]
    commands = list(map(str.lower, commands))

    for command in commands:
        if " " in command:
            command: str = command.split(" ")[0]
        print(timeit.timeit("check_owo_command(command)", globals=globals(), number=1000000))
        print(timeit.timeit("command in owo_commands", globals=globals(), number=1000000))
