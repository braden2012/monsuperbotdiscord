import asyncio
import discord
from discord.ext import commands
import os
import os
import psycopg2

# Railway donne automatiquement cette variable à ton bot
DATABASE_URL = os.getenv('DATABASE_URL')

# Pour te connecter à ta base de données dans tes fonctions, tu feras :
# conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# 1. Configuration des intentions (Intents)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 2. Initialisation du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# 3. Événement de démarrage
@bot.event
async def on_ready():
    print(f"🧬 Squelette activé : {bot.user.name} est en ligne !")
    try:
        synced = await bot.tree.sync()
        print(f"🔗 {len(synced)} commandes slash synchronisées.")
    except Exception as e:
        print(f"❌ Erreur de synchro : {e}")

# 4. Chargement automatique des fichiers de commandes (Cogs)
async def load_extensions():
    # Crée un dossier 'cogs' s'il n'existe pas
    if not os.path.exists("cogs"):
        os.makedirs("cogs")
        
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            # Charge le fichier en enlevant l'extension .py
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"📦 Module chargé : {filename}")

# 5. Lancement du programme
async def main():
    async with bot:
        await load_extensions()
        await bot.start("TON_TOKEN_SECRET_ICI")

# Exécution du script
if __name__ == "__main__":
    asyncio.run(main())
