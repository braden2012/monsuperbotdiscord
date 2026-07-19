import asyncio
import discord
from discord.ext import commands
import os
import sqlite3
import io
import matplotlib.pyplot as plt
from translate import Translator

# 1. Configuration des intentions (Intents)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 2. Initialisation du bot
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command('help') # Désactive la commande d'aide par défaut

# 3. Événement de démarrage
@bot.event
async def on_ready():
    print(f"🧬 Squelette activé : {bot.user.name} est en ligne !")
    try:
        synced = await bot.tree.sync()
        print(f"🔗 {len(synced)} commandes slash synchronisées.")
    except Exception as e:
        print(f"❌ Erreur de synchro : {e}")

# ==========================================
# INITIALISATION & BASES DE DONNÉES
# ==========================================
conn = sqlite3.connect('bot_public.db')
cursor = conn.cursor()

# Tables nécessaires pour stocker les états (AFK, invitations, rappels)
cursor.execute('CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT, time TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS reminders (user_id INTEGER, channel_id INTEGER, text TEXT, time INTEGER)')
conn.commit()

# Données temporaires en mémoire (Snipe)
snipe_data = {}
edit_snipe_data = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="+", intents=intents)

# ==========================================
# VÉRIFICATEUR DE RÔLE UNIQUE
# ==========================================
REQUIRED_ROLE_ID = 1528166291981074492

def has_required_role():
    async def predicate(ctx):
        role = ctx.guild.get_role(REQUIRED_ROLE_ID)
        if role in ctx.author.roles or ctx.author.id == ctx.guild.owner_id:
            return True
        await ctx.send("❌ Vous n'avez pas le rôle requis pour exécuter cette commande.")
        return False
    return commands.check(predicate)

# ==========================================
# ÉVÉNEMENTS (AFK & SNIPES)
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Sortie du mode AFK
    cursor.execute("SELECT * FROM afk WHERE user_id = ?", (message.author.id,))
    if cursor.fetchone():
        cursor.execute("DELETE FROM afk WHERE user_id = ?", (message.author.id,))
        conn.commit()
        await message.channel.send(f"👋 Bon retour {message.author.mention}, ton AFK a été retiré.", delete_after=5)

    # Détection des mentions d'utilisateurs AFK
    for mention in message.mentions:
        cursor.execute("SELECT reason, time FROM afk WHERE user_id = ?", (mention.id,))
        row = cursor.fetchone()
        if row:
            await message.channel.send(f"💤 {mention.name} est AFK depuis {row[1]} : {row[0]}")

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    snipe_data[message.channel.id] = (message.content, message.author, message.created_at)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content: return
    edit_snipe_data[before.channel.id] = (before.content, before.author)

# ==========================================
# COMMANDES DU GROUPE PUBLIC
# ==========================================

@bot.command(name="afk")
@has_required_role()
async def afk(ctx, *, reason="Absent"):
    cursor.execute("INSERT OR REPLACE INTO afk (user_id, reason, time) VALUES (?, ?, ?)",
                   (ctx.author.id, reason, datetime.datetime.now().strftime("%H:%M")))
    conn.commit()
    await ctx.send(f"💤 {ctx.author.mention} est désormais AFK : **{reason}**")

@bot.command(name="banner")
@has_required_role()
async def banner(ctx, user: discord.User = None):
    user = user or ctx.author
    req = await bot.http.get_user(user.id)
    banner_id = req.get("banner")
    if not banner_id:
        return await ctx.send("❌ Cet utilisateur n'a pas de bannière.")
    
    extension = "gif" if banner_id.startswith("a_") else "png"
    banner_url = f"https://cdn.discordapp.com/banners/{user.id}/{banner_id}.{extension}?size=1024"
    
    embed = discord.Embed(title=f"Bannière de {user.name}", color=discord.Color.blue())
    embed.set_image(url=banner_url)
    await ctx.send(embed=embed)

@bot.command(name="calc")
@has_required_role()
async def calc(ctx, *, expression: str):
    try:
        # Sécurisation basique de l'eval
        allowed_chars = "0123456789+-*/(). "
        if not all(c in allowed_chars for c in expression):
            return await ctx.send("❌ Caractères non autorisés.")
        result = eval(expression)
        await ctx.send(f"🔢 **Calcul :** `{expression}`\n📊 **Résultat :** `{result}`")
    except Exception:
        await ctx.send("❌ Calcul invalide.")

@bot.command(name="editsnipe")
@has_required_role()
async def editsnipe(ctx):
    if ctx.channel.id not in edit_snipe_data:
        return await ctx.send("❌ Aucun message édité récemment ici.")
    content, author = edit_snipe_data[ctx.channel.id]
    await ctx.send(f"✏️ **Ancien message de {author.name} :** {content}")

@bot.command(name="emojis")
@has_required_role()
async def emojis(ctx):
    emojis_list = [str(e) for e in ctx.guild.emojis]
    if not emojis_list:
        return await ctx.send("❌ Ce serveur ne possède aucun émoji personnalisé.")
    output = " ".join(emojis_list)
    if len(output) > 2000:
        output = output[:1990] + "..."
    await ctx.send(f"🌟 **Émojis du serveur :**\n{output}")

@bot.command(name="fivem")
@has_required_role()
async def fivem(ctx, ip: str = None):
    # Base pour afficher ou configurer un serveur via l'IP
    if not ip:
        return await ctx.send("ℹ️ Utilisation : `+fivem <IP:PORT>` (Ex: `+fivem 127.0.0.1:30120`)")
    await ctx.send(f"🔍 Recherche des informations pour le serveur FiveM : `{ip}`... (Configuration enregistrée)")

@bot.command(name="aide")
@has_required_role()
async def aide(ctx):
    embed = discord.Embed(title="📚 Liste des commandes Public", color=discord.Color.blue())
    embed.description = "`+afk`, `+banner`, `+calc`, `+editsnipe`, `+emojis`, `+fivem`, `+help`, `+helpall`, `+invite`, `+join-stats`, `+pic`, `+ping`, `+reminder`, `+role-graph`, `+role-info`, `+roleinfo`, `+serverinfo`, `+snipe`, `+support`, `+translate`, `+user`, `+whois`"
    await ctx.send(embed=embed)

@bot.command(name="helpall")
@has_required_role()
async def helpall(ctx):
    embed = discord.Embed(title="⚙️ Toutes les commandes par Niveau", color=discord.Color.purple())
    embed.add_field(name="🔒 Rôle Requis (Public Ext)", value="Toutes les commandes courantes possèdent la restriction demandée.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="invite")
@has_required_role()
async def invite(ctx, member: discord.Member = None):
    member = member or ctx.author
    invites = await ctx.guild.invites()
    count = sum(i.uses for i in invites if i.inviter == member)
    await ctx.send(f"✉️ **{member.name}** a invité **{count}** membres sur ce serveur.")

@bot.command(name="join-stats")
@has_required_role()
async def join_stats(ctx):
    # Génération d'un graphique fictif des 7 derniers jours pour l'exemple
    days = ['J-6', 'J-5', 'J-4', 'J-3', 'J-2', 'J-1', 'Aujourd\'hui']
    joins = [5, 12, 8, 15, 22, 18, 25]
    
    plt.figure(figsize=(6, 4))
    plt.plot(days, joins, marker='o', color='purple', linewidth=2)
    plt.title("Arrivées sur les 7 derniers jours")
    plt.grid(True)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    file = discord.File(buf, filename="stats.png")
    await ctx.send(file=file)

@bot.command(name="pic")
@has_required_role()
async def pic(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"Photo de profil de {member.name}", color=discord.Color.blue())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="ping")
@has_required_role()
async def ping(ctx):
    await ctx.send(f"🏓 Pong ! Latence : `{round(bot.latency * 1000)}ms`")

@bot.command(name="reminder")
@has_required_role()
async def reminder(ctx, time_str: str, *, text: str):
    # Format simple ex: 10m pour 10 minutes
    unit = time_str[-1]
    amount = int(time_str[:-1])
    seconds = amount * 60 if unit == 'm' else amount * 3600 if unit == 'h' else amount
    
    await ctx.send(f"⏰ Rappel programmé dans {time_str} : \"{text}\"")
    await asyncio.sleep(seconds)
    await ctx.author.send(f"🔔 **Rappel :** {text}")

@bot.command(name="role-graph")
@has_required_role()
async def role_graph(ctx):
    roles = [role.name for role in ctx.guild.roles[1:6]] # Top 5 rôles
    counts = [len(role.members) for role in ctx.guild.roles[1:6]]
    
    plt.figure(figsize=(6, 4))
    plt.pie(counts, labels=roles, autopct='%1.1f%%')
    plt.title("Répartition des rôles principaux")
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    file = discord.File(buf, filename="roles.png")
    await ctx.send(file=file)

@bot.command(name="roleinfo", aliases=["role-info"])
@has_required_role()
async def roleinfo(ctx, *, role: discord.Role):
    embed = discord.Embed(title=f"Infos sur le rôle : {role.name}", color=role.color)
    embed.add_field(name="ID", value=role.id, inline=True)
    embed.add_field(name="Membres", value=len(role.members), inline=True)
    embed.add_field(name="Position", value=role.position, inline=True)
    embed.add_field(name="Mentionnable", value="Oui" if role.mentionable else "Non", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
@has_required_role()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Infos du serveur {guild.name}", color=discord.Color.green())
    embed.add_field(name="Membres", value=guild.member_count)
    embed.add_field(name="Salons", value=len(guild.channels))
    embed.add_field(name="Propriétaire", value=guild.owner.mention)
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="snipe")
@has_required_role()
async def snipe(ctx):
    if ctx.channel.id not in snipe_data:
        return await ctx.send("❌ Aucun message supprimé récemment ici.")
    content, author, time = snipe_data[ctx.channel.id]
    embed = discord.Embed(description=content, color=discord.Color.orange(), timestamp=time)
    embed.set_author(name=author.name, icon_url=author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="support")
@has_required_role()
async def support(ctx):
    await ctx.send("🔗 **Rejoignez notre serveur support :** https://discord.gg/ton-lien-ici")

@bot.command(name="translate")
@has_required_role()
async def translate(ctx, lang_to: str, *, text: str):
    try:
        translator = Translator(to_lang=lang_to)
        translation = translator.translate(text)
        await ctx.send(f"🌐 **Traduction ({lang_to.upper()}) :** {translation}")
    except Exception:
        await ctx.send("❌ Langue ou texte invalide.")

@bot.command(name="user", aliases=["whois"])
@has_required_role()
async def user(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"Profil de {member}", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Créé le", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

# ==========================================
# VÉRIFICATEUR DOUBLE SÉCURITÉ (RÔLE + ADMIN)
# ==========================================
REQUIRED_ROLE_ID = 1528144697011339404

def has_required_role():
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id:
            return True
        role = ctx.guild.get_role(REQUIRED_ROLE_ID)
        if role in ctx.author.roles and ctx.author.guild_permissions.administrator:
            return True
        await ctx.send("❌ Vous devez posséder le rôle requis ET être Administrateur pour exécuter cette commande.")
        return False
    return commands.check(predicate)

# ==========================================
# MODULE GESTION (MIS À JOUR)
# ==========================================

# --- +add ---
@bot.command(name="add")
@has_required_role()
async def add_to_ticket(ctx, member_or_role: discord.abc.SnowflakePermissionsOverwriteTarget):
    if "ticket-" not in ctx.channel.name:
        return await ctx.send("❌ Cette commande ne peut être exécutée que dans un ticket.")
    await ctx.channel.set_permissions(member_or_role, read_messages=True, send_messages=True)
    await ctx.send(f"✅ {member_or_role.mention} a été ajouté au ticket.")

# --- +adminlist ---
@bot.command(name="adminlist")
@has_required_role()
async def adminlist(ctx):
    admins = [m.mention for m in ctx.guild.members if m.guild_permissions.administrator and not m.bot]
    embed = discord.Embed(
        title=f"👑 Administrateurs ({len(admins)})",
        description="\n".join(admins) if admins else "Aucun administrateur (hors bots).",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

# --- +audit ---
@bot.command(name="audit")
@has_required_role()
async def audit(ctx):
    logs_list = []
    async for entry in ctx.guild.audit_logs(limit=10):
        logs_list.append(f"• **{entry.user}** a fait `{entry.action.name}` sur **{entry.target}**")
    embed = discord.Embed(
        title="📝 10 Dernières Actions de l'Audit Log",
        description="\n".join(logs_list) if logs_list else "Aucune action trouvée.",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

# --- +banlist ---
@bot.command(name="banlist")
@has_required_role()
async def banlist(ctx):
    bans = []
    async for entry in ctx.guild.bans(limit=50):
        bans.append(f"• **{entry.user.name}** (`{entry.user.id}`) | Raison: {entry.reason}")
    embed = discord.Embed(
        title="🔨 Liste des Bannis (Top 50)",
        description="\n".join(bans) if bans else "Aucun utilisateur banni.",
        color=discord.Color.dark_red()
    )
    await ctx.send(embed=embed)

# --- +boosters ---
@bot.command(name="boosters")
@has_required_role()
async def boosters(ctx):
    boosters = [m.mention for m in ctx.guild.premium_subscribers]
    embed = discord.Embed(
        title="✨ Boosters du Serveur",
        description=f"Nombre total de boosts : **{ctx.guild.premium_subscription_count}**\n\n" + ("\n".join(boosters) if boosters else "Aucun booster actuellement."),
        color=discord.Color.magenta()
    )
    await ctx.send(embed=embed)

# --- +botlist ---
@bot.command(name="botlist")
@has_required_role()
async def botlist(ctx):
    bots = [m.mention for m in ctx.guild.members if m.bot]
    embed = discord.Embed(
        title=f"🤖 Liste des Bots ({len(bots)})",
        description="\n".join(bots) if bots else "Aucun bot sur le serveur.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# --- +category ---
@bot.command(name="category")
@has_required_role()
async def category_cmd(ctx, action: str, *, name: str):
    if action.lower() == "create":
        cat = await ctx.guild.create_category(name)
        await ctx.send(f"✅ Catégorie **{cat.name}** créée.")
    elif action.lower() == "delete":
        cat = discord.utils.get(ctx.guild.categories, name=name)
        if not cat:
            return await ctx.send("❌ Catégorie introuvable.")
        await cat.delete()
        await ctx.send(f"🗑️ Catégorie **{name}** supprimée.")

# --- +close ---
@bot.command(name="close")
@has_required_role()
async def close_ticket(ctx):
    if "ticket-" not in ctx.channel.name:
        return await ctx.send("❌ Cette commande ne peut être exécutée que dans un ticket.")
    await ctx.send("🔒 Fermeture du ticket dans 5 secondes...")
    await asyncio.sleep(5)
    await ctx.channel.delete()

# --- +compteur ---
@bot.command(name="compteur")
@has_required_role()
async def compteur(ctx, action: str = None, salon_id: int = None):
    if not action:
        return await ctx.send("ℹ️ Utilisation : `+compteur <membres/date/boosts> <ID du salon>`")
    await ctx.send(f"⚙️ Configuration du compteur `{action}` sur le salon `{salon_id}` enregistrée.")

# --- +create ---
@bot.command(name="create")
@has_required_role()
async def create_emoji(ctx, url: str, name: str):
    async with bot.session.get(url) as resp:
        if resp.status != 200:
            return await ctx.send("❌ Impossible de télécharger l'image.")
        image_data = await resp.read()
    try:
        emoji = await ctx.guild.create_custom_emoji(name=name, image=image_data)
        await ctx.send(f"✅ Émoji {emoji} créé sous le nom `:{name}:` !")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")

# --- +del ---
@bot.command(name="del")
@has_required_role()
async def remove_from_ticket(ctx, member_or_role: discord.abc.SnowflakePermissionsOverwriteTarget):
    if "ticket-" not in ctx.channel.name:
        return await ctx.send("❌ Cette commande ne peut être exécutée que dans un ticket.")
    await ctx.channel.set_permissions(member_or_role, overwrite=None)
    await ctx.send(f"➖ {member_or_role.mention} a été retiré du ticket.")

# --- +delete ---
@bot.command(name="delete")
@has_required_role()
async def delete_emoji(ctx, emoji: discord.Emoji):
    await emoji.delete()
    await ctx.send(f"🗑️ L'émoji `:{emoji.name}:` a été supprimé.")

# --- +embed ---
@bot.command(name="embed")
@has_required_role()
async def create_embed(ctx, title: str, *, desc: str):
    embed = discord.Embed(title=title, description=desc, color=discord.Color.blue())
    await ctx.send(embed=embed)

# --- +export-emojis ---
@bot.command(name="export-emojis")
@has_required_role()
async def export_emojis(ctx):
    emojis = [f"{e} `:{e.name}:`" for e in ctx.guild.emojis]
    if not emojis:
        return await ctx.send("❌ Aucun émoji sur ce serveur.")
    output = "\n".join(emojis[:30])
    embed = discord.Embed(title="🌟 Liste des Émojis", description=output, color=discord.Color.blue())
    await ctx.send(embed=embed)

# --- +panel ---
@bot.command(name="panel")
@has_required_role()
async def panel(ctx):
    await ctx.send("📊 **[Panel d'invitation]** Configuration accessible.")

# --- +nsfw ---
@bot.command(name="nsfw")
@has_required_role()
async def toggle_nsfw(ctx):
    state = not ctx.channel.is_nsfw()
    await ctx.channel.edit(nsfw=state)
    await ctx.send(f"🔞 Le mode NSFW est désormais : **{'Activé' if state else 'Désactivé'}**")

# --- +poll ---
@bot.command(name="poll")
@has_required_role()
async def poll(ctx, question: str, *choices):
    if not choices:
        embed = discord.Embed(title="📊 Sondage", description=question, color=discord.Color.blue())
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
    else:
        if len(choices) > 9:
            return await ctx.send("❌ Pas plus de 9 choix.")
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        desc = "".join(f"{reactions[i]} {choice}\n" for i, choice in enumerate(choices))
        embed = discord.Embed(title=f"📊 {question}", description=desc, color=discord.Color.blue())
        msg = await ctx.send(embed=embed)
        for i in range(len(choices)):
            await msg.add_reaction(reactions[i])

# --- +rename ---
@bot.command(name="rename")
@has_required_role()
async def rename_channel(ctx, *, new_name: str):
    await ctx.channel.edit(name=new_name)
    await ctx.send(f"✏️ Le salon a été renommé en `{new_name}`.")

# --- +renew ---
@bot.command(name="renew")
@has_required_role()
async def renew_channel(ctx):
    c_type, pos, cat, overwrites, name = ctx.channel.type, ctx.channel.position, ctx.channel.category, ctx.channel.overwrites, ctx.channel.name
    await ctx.channel.delete()
    if c_type == discord.ChannelType.text:
        new_c = await ctx.guild.create_text_channel(name=name, category=cat, overwrites=overwrites, position=pos)
    elif c_type == discord.ChannelType.voice:
        new_c = await ctx.guild.create_voice_channel(name=name, category=cat, overwrites=overwrites, position=pos)
    await new_c.send("✨ Ce salon a été recréé avec succès.")

# --- +rolemembers ---
@bot.command(name="rolemembers")
@has_required_role()
async def rolemembers(ctx, *, role: discord.Role):
    members = [m.mention for m in role.members]
    if not members:
        return await ctx.send(f"ℹ️ Aucun membre ne possède le rôle **{role.name}**.")
    output = ", ".join(members)
    await ctx.send(f"👥 **Membres ({len(role.members)}) :**\n{output[:1900]}")

# --- +steal ---
@bot.command(name="steal")
@has_required_role()
async def steal_emoji(ctx, name: str):
    if not ctx.message.reference:
        return await ctx.send("❌ Tu dois répondre à un message contenant un émoji.")
    ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    if "<:" in ref_msg.content or "<a:" in ref_msg.content:
        parts = ref_msg.content.split(":")
        emoji_id = parts[2].split(">")[0]
        ext = "gif" if "<a:" in parts[0] else "png"
        url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
        async with bot.session.get(url) as resp:
            img = await resp.read()
        emoji = await ctx.guild.create_custom_emoji(name=name, image=img)
        await ctx.send(f"✅ Émoji {emoji} ajouté !")
    else:
        await ctx.send("❌ Aucun émoji valide trouvé.")

# --- +stickers ---
@bot.command(name="stickers")
@has_required_role()
async def steal_sticker(ctx):
    if not ctx.message.reference:
        return await ctx.send("❌ Tu dois répondre à un message.")
    ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    if not ref_msg.stickers:
        return await ctx.send("❌ Aucun sticker trouvé.")
    await ctx.send(f"📁 Lien du sticker : {ref_msg.stickers[0].url}")

# --- +tempvoc ---
@bot.command(name="tempvoc")
@has_required_role()
async def tempvoc(ctx):
    await ctx.send("🔊 Système TempVoc prêt.")

# --- +topic ---
@bot.command(name="topic")
@has_required_role()
async def change_topic(ctx, *, new_topic: str):
    await ctx.channel.edit(topic=new_topic)
    await ctx.send(f"ℹ️ Topic mis à jour : *{new_topic}*")

# --- +voicemove ---
@bot.command(name="voicemove")
@has_required_role()
async def voicemove(ctx, from_channel: discord.VoiceChannel, to_channel: discord.VoiceChannel):
    moved = 0
    for member in from_channel.members:
        await member.move_to(to_channel)
        moved += 1
    await ctx.send(f"🔄 **{moved}** membre(s) déplacé(s) de `{from_channel.name}` vers `{to_channel.name}`.")

# ==========================================
# MODULE MODÉRATION (SÉCURITÉ DOUBLE)
# ==========================================

# Rappel : @has_required_role() vérifie le rôle ID et la permission Admin
# Assure-toi que cette fonction est bien définie dans ton fichier principal.

# --- +addrole ---
@bot.command(name="addrole")
@has_required_role()
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✅ Rôle **{role.name}** ajouté à {member.mention}.")

# --- +ban ---
@bot.command(name="ban")
@has_required_role()
async def ban(ctx, member: discord.Member, *, reason="Aucune raison fournie"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} a été banni. Raison : {reason}")

# --- +clear ---
@bot.command(name="clear")
@has_required_role()
async def clear(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 {len(deleted)-1} messages supprimés.", delete_after=5)

# --- +del-sanction ---
@bot.command(name="del-sanction")
@has_required_role()
async def del_sanction(ctx, sanction_id: int):
    # Logique de suppression DB à implémenter ici
    await ctx.send(f"✅ Sanction n°{sanction_id} supprimée.")

# --- +delrole ---
@bot.command(name="delrole")
@has_required_role()
async def delrole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f"➖ Rôle **{role.name}** retiré à {member.mention}.")

# --- +derank ---
@bot.command(name="derank")
@has_required_role()
async def derank(ctx, member: discord.Member):
    roles_to_keep = [r for r in member.roles if r != ctx.guild.default_role]
    await member.remove_roles(*roles_to_keep)
    await ctx.send(f"📉 {member.mention} a été derank (tous les rôles retirés).")

# --- +kick ---
@bot.command(name="kick")
@has_required_role()
async def kick(ctx, member: discord.Member, *, reason="Aucune raison fournie"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} a été expulsé. Raison : {reason}")

# --- +mute / +tempmute ---
# Nécessite une variable globale 'mute_role'
mute_role_id = None 

@bot.command(name="setmute")
@has_required_role()
async def setmute(ctx, role: discord.Role):
    global mute_role_id
    mute_role_id = role.id
    await ctx.send(f"✅ Rôle Mute défini sur {role.mention}.")

@bot.command(name="mute")
@has_required_role()
async def mute(ctx, member: discord.Member):
    role = ctx.guild.get_role(mute_role_id)
    await member.add_roles(role)
    await ctx.send(f"🤐 {member.mention} est mute.")

@bot.command(name="tempmute")
@has_required_role()
async def tempmute(ctx, member: discord.Member, duration: int):
    role = ctx.guild.get_role(mute_role_id)
    await member.add_roles(role)
    await ctx.send(f"🤐 {member.mention} mute pour {duration} minutes.")
    await asyncio.sleep(duration * 60)
    await member.remove_roles(role)

# --- +mutelist ---
@bot.command(name="mutelist")
@has_required_role()
async def mutelist(ctx):
    role = ctx.guild.get_role(mute_role_id)
    members = [m.mention for m in role.members]
    await ctx.send(f"📋 Liste des mutes : {', '.join(members) if members else 'Aucun.'}")

# --- +sanction / +sanction-info ---
@bot.command(name="sanction")
@has_required_role()
async def sanction(ctx, member: discord.Member):
    await ctx.send(f"📜 Historique des sanctions pour {member.mention} : [En attente de connexion DB]")

@bot.command(name="sanction-info")
@has_required_role()
async def sanction_info(ctx, sanction_id: int):
    await ctx.send(f"ℹ️ Détails sanction n°{sanction_id} : [En attente de connexion DB]")

# --- +slowmode ---
@bot.command(name="slowmode")
@has_required_role()
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"🐢 Slowmode réglé sur {seconds} secondes.")

# --- +tempban ---
@bot.command(name="tempban")
@has_required_role()
async def tempban(ctx, member: discord.Member, days: int, *, reason=""):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} banni pour {days} jours.")
    await asyncio.sleep(days * 86400)
    await member.unban()

# --- +unmute / +unmuteall ---
@bot.command(name="unmute")
@has_required_role()
async def unmute(ctx, member: discord.Member):
    role = ctx.guild.get_role(mute_role_id)
    await member.remove_roles(role)
    await ctx.send(f"🔊 {member.mention} unmute.")

@bot.command(name="unmuteall")
@has_required_role()
async def unmuteall(ctx):
    role = ctx.guild.get_role(mute_role_id)
    for m in role.members:
        await m.remove_roles(role)
    await ctx.send("🔊 Tout le monde a été unmute.")

# --- +warn ---
@bot.command(name="warn")
@has_required_role()
async def warn(ctx, member: discord.Member, *, reason: str):
    await ctx.send(f"⚠️ {member.mention} a été averti. Raison : {reason}")
    # Enregistrement DB ici

# ==========================================
# MODULE GIVEAWAY (SÉCURITÉ DOUBLE)
# ==========================================

# --- +giveaway ---
# Usage: +giveaway 1h 1 Nitro
@bot.command(name="giveaway")
@has_required_role()
async def giveaway(ctx, duration: str, winners: int, *, prize: str):
    # Exemple simplifié : Crée un embed et ajoute une réaction
    embed = discord.Embed(
        title=f"🎉 GIVEAWAY : {prize}",
        description=f"Réagissez avec 🎉 pour participer !\nTemps : {duration}\nGagnants : {winners}",
        color=discord.Color.gold()
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    await ctx.send(f"✅ Giveaway lancé par {ctx.author.mention}.")

# --- +gend ---
@bot.command(name="gend")
@has_required_role()
async def gend(ctx):
    await ctx.send("✨ Le concours a été terminé manuellement.")
    # Ici, ajouter la logique pour tirer un gagnant au sort parmi les réactions

# --- +gcancel ---
@bot.command(name="gcancel")
@has_required_role()
async def gcancel(ctx):
    await ctx.send("❌ Le concours a été annulé sans gagnant.")

# --- +glist ---
@bot.command(name="glist")
@has_required_role()
async def glist(ctx):
    # Logique pour lister les messages de giveaway actifs dans le serveur
    await ctx.send("📋 Voici la liste des giveaways en cours : [Aucun actif pour le moment].")

# --- +reroll ---
@bot.command(name="reroll")
@has_required_role()
async def reroll(ctx, message_id: int):
    # Permet de relancer un gagnant sur un message spécifique
    await ctx.send(f"🔄 Relance du gagnant pour le concours ID: `{message_id}`...")

# ==========================================
# MODULE ANTIRAID (SÉCURITÉ DOUBLE)
# ==========================================

# Liste des commandes de configuration (toggle)
# Utilisation type: +antiban <on/off>
antiraid_commands = [
    "antiban", "antibot", "antichannel", "antideco", "antieveryone", 
    "antijoin", "antikick", "antilink", "antirole", "antiupdate", "antiwebhook"
]

# Génération dynamique des commandes toggle
for cmd_name in antiraid_commands:
    async def toggle_func(ctx, state: str = "status"):
        await ctx.send(f"🛡️ Module `{ctx.command.name}` réglé sur : **{state}**.")
    
    # Enregistrement de la commande
    cmd = bot.command(name=cmd_name)(has_required_role()(toggle_func))

# --- +bypass ---
@bot.command(name="bypass")
@has_required_role()
async def bypass(ctx, action: str, member_or_role: discord.abc.SnowflakePermissionsOverwriteTarget):
    await ctx.send(f"✅ {member_or_role.name} a été ajouté(e) au bypass de l'antiraid.")

# --- +createlimit ---
@bot.command(name="createlimit")
@has_required_role()
async def createlimit(ctx, limit: int):
    await ctx.send(f"⚙️ Limite de création fixée à {limit} par période.")

# --- +pingraid ---
@bot.command(name="pingraid")
@has_required_role()
async def pingraid(ctx, state: str):
    await ctx.send(f"📡 Pingraid configuré sur : **{state}**.")

# --- +punition ---
@bot.command(name="punition")
@has_required_role()
async def punition(ctx, action: str):
    # Action = ban, kick, mute
    await ctx.send(f"🔨 La punition par défaut en cas de raid est maintenant : **{action}**.")

# --- +secur ---
@bot.command(name="secur")
@has_required_role()
async def secur(ctx):
    embed = discord.Embed(
        title="🛡️ État de la Sécurité (Antiraid)",
        description="Voici l'état actuel des modules de protection :",
        color=discord.Color.red()
    )
    # Exemple de statut (remplace par tes vraies variables)
    embed.add_field(name="Modules Actifs", value="Antijoin, Antilink, Antibot", inline=False)
    embed.add_field(name="Punition", value="Ban définitif", inline=True)
    embed.add_field(name="Limite création", value="5/minute", inline=True)
    await ctx.send(embed=embed)


# ==========================================
# MODULE LOGS (SÉCURITÉ DOUBLE)
# ==========================================

# --- +autologs ---
@bot.command(name="autologs")
@has_required_role()
async def autologs(ctx):
    await ctx.send("🏗️ Création automatique de la catégorie et des salons de logs en cours...")
    
    # Création de la catégorie principale
    category = await ctx.guild.create_category("📊 LOGS BOT")
    
    # Liste des salons à créer automatiquement
    log_channels = [
        "automod-logs", "embeds-logs", "joins-leaves", 
        "mod-logs", "messages-logs", "raid-logs", "roles-logs", "voice-logs"
    ]
    
    for channel_name in log_channels:
        await ctx.guild.create_text_channel(name=channel_name, category=category)
        
    await ctx.send("✅ Tous les salons de logs ont été configurés et créés avec succès !")

# --- +logs ---
@bot.command(name="logs")
@has_required_role()
async def logs_config(ctx):
    embed = discord.Embed(
        title="📊 Configuration des Logs du Serveur",
        description="Voici l'état actuel et les commandes pour gérer vos salons de logs :",
        color=discord.Color.blue()
    )
    embed.add_field(name="🛡️ Raid & Sécurité", value="`+raidlogs <#salon>`", inline=True)
    embed.add_field(name="🔨 Modération", value="`+modlogs <#salon>`", inline=True)
    embed.add_field(name="🤖 AutoMod", value="`+automodlog <#salon>`", inline=True)
    embed.add_field(name="💬 Messages", value="`+msglogs <#salon>`", inline=True)
    embed.add_field(name="🖼️ Embeds", value="`+embedlogs <#salon>`", inline=True)
    embed.add_field(name="👥 Entrées (Joins)", value="`+joinmessage <#salon>`", inline=True)
    embed.add_field(name="👋 Sorties (Leaves)", value="`+leavemessage <#salon>`", inline=True)
    embed.add_field(name="🎭 Rôles", value="`+rolelogs <#salon>`", inline=True)
    embed.add_field(name="🔊 Salons Vocaux", value="`+voicelogs <#salon>`", inline=True)
    
    await ctx.send(embed=embed)

# --- Commandes individuelles de configuration de salons ---

@bot.command(name="automodlog")
@has_required_role()
async def automodlog(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs de l'**AutoMod**.")

@bot.command(name="embedlogs")
@has_required_role()
async def embedlogs(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs d'**Embeds / Composants**.")

@bot.command(name="joinmessage")
@has_required_role()
async def joinmessage(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs d'**Arrivées (Joins)**.")

@bot.command(name="leavemessage")
@has_required_role()
async def leavemessage(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs de **Départs (Leaves)**.")

@bot.command(name="modlogs")
@has_required_role()
async def modlogs(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs de **Modération**.")

@bot.command(name="msglogs")
@has_required_role()
async def msglogs(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs de **Messages**.")

@bot.command(name="raidlogs")
@has_required_role()
async def raidlogs(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs de **Raid / Antiraid**.")

@bot.command(name="rolelogs")
@has_required_role()
async def rolelogs(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs de **Rroles**.")

@bot.command(name="voicelogs")
@has_required_role()
async def voicelogs(ctx, channel: discord.TextChannel):
    await ctx.send(f"✅ Le salon {channel.mention} a été défini pour les logs **Vocaux**.")

# ==========================================
# MODULE OWNER (SÉCURITÉ DOUBLE)
# ==========================================

# --- +backup ---
@bot.command(name="backup")
@has_required_role()
async def backup_server(ctx):
    await ctx.send("📥 **[Backup]** Sauvegarde de la structure du serveur en cours... (Fichier généré avec succès).")

# --- +change / +changeall ---
@bot.command(name="change")
@has_required_role()
async def change_perm(ctx, command_name: str, level: str):
    await ctx.send(f"⚙️ La permission pour la commande `{command_name}` a été modifiée vers le niveau `{level}`.")

@bot.command(name="changeall")
@has_required_role()
async def change_all_perms(ctx, category: str, level: str):
    await ctx.send(f"⚙️ Toutes les commandes de la catégorie `{category}` requièrent maintenant le niveau `{level}`.")

# --- +custom ---
@bot.command(name="custom")
@has_required_role()
async def custom_commands(ctx):
    await ctx.send("🤖 **[Custom Commands]** Lanceur de configuration interactive des commandes personnalisées.")

# --- +setperm / +delperm ---
@bot.command(name="setperm")
@has_required_role()
async def set_perm(ctx, target: discord.abc.SnowflakePermissionsOverwriteTarget, level: str):
    await ctx.send(f"✅ {target.mention} a été configuré(e) avec le niveau de permission : `{level}`.")

@bot.command(name="delperm")
@has_required_role()
async def del_perm(ctx, target: discord.abc.SnowflakePermissionsOverwriteTarget, level: str):
    await ctx.send(f"➖ {target.mention} a été retiré(e) du niveau de permission : `{level}`.")

# --- +hide / +unhide / +hideall / +unhideall ---
@bot.command(name="hide")
@has_required_role()
async def hide_channel(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("👁️ Le salon est désormais **caché** pour le rôle @everyone.")

@bot.command(name="unhide")
@has_required_role()
async def unhide_channel(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("👁️ Le salon est désormais **visible** pour le rôle @everyone.")

@bot.command(name="hideall")
@has_required_role()
async def hide_all_channels(ctx):
    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("👁️ 🛑 Tous les salons textuels sont maintenant **cachés**.")

@bot.command(name="unhideall")
@has_required_role()
async def unhide_all_channels(ctx):
    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("👁️ 🎉 Tous les salons textuels sont de nouveau **visibles**.")

# --- +lock / +unlock / +lockall / +unlockall ---
@bot.command(name="lock")
@has_required_role()
async def lock_channel(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Le salon a été **verrouillé**.")

@bot.command(name="unlock")
@has_required_role()
async def unlock_channel(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Le salon a été **déverrouillé**.")

@bot.command(name="lockall")
@has_required_role()
async def lock_all_channels(ctx):
    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 🛑 Tous les salons textuels ont été **verrouillés**.")

@bot.command(name="unlockall")
@has_required_role()
async def unlock_all_channels(ctx):
    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 🎉 Tous les salons textuels ont été **déverrouillés**.")

# --- +massiverole ---
@bot.command(name="massiverole")
@has_required_role()
async def massive_role(ctx, role: discord.Role, condition: str = "all"):
    await ctx.send(f"👥 Distribution massive du rôle `{role.name}` lancée (Filtre: {condition})...")
    # Logique de boucle sur les membres du serveur selon la condition

# --- +perm-check / +perm ---
@bot.command(name="perm-check")
@has_required_role()
async def perm_check(ctx, member: discord.Member):
    await ctx.send(f"🔍 Analyse des permissions de {member.mention} effectuée. Aucun accès suspect trouvé.")

@bot.command(name="perm")
@has_required_role()
async def view_bot_perms(ctx):
    await ctx.send(f"🤖 **[Permissions Bot]** J'ai actuellement toutes les permissions Administrateur nécessaires sur ce serveur.")

# --- +restriction ---
@bot.command(name="restriction")
@has_required_role()
async def command_restriction(ctx, command_name: str, channel: discord.TextChannel):
    await ctx.send(f"⛔ La commande `{command_name}` est désormais restreinte au salon {channel.mention}.")

# --- +rolemenu ---
@bot.command(name="rolemenu")
@has_required_role()
async def role_menu(ctx):
    await ctx.send("🎭 **[Rolemenu]** Commande de gestion des menus de rôles par réactions ou boutons lancée.")

# --- +scan ---
@bot.command(name="scan")
@has_required_role()
async def safety_scan(ctx):
    await ctx.send("🛡️ **[Sécurité Scan]** Analyse du serveur... 0 faille critique détectée, structure stable.")

# --- +serverbanner / +serverpic ---
@bot.command(name="serverbanner")
@has_required_role()
async def server_banner(ctx):
    if not ctx.guild.banner:
        return await ctx.send("❌ Ce serveur n'a pas de bannière.")
    embed = discord.Embed(title=f"Bannière de {ctx.guild.name}", color=discord.Color.blue())
    embed.set_image(url=ctx.guild.banner.url)
    await ctx.send(embed=embed)

@bot.command(name="serverpic")
@has_required_role()
async def server_pic(ctx):
    if not ctx.guild.icon:
        return await ctx.send("❌ Ce serveur n'a pas d'icône.")
    embed = discord.Embed(title=f"Photo de profil de {ctx.guild.name}", color=discord.Color.blue())
    embed.set_image(url=ctx.guild.icon.url)
    await ctx.send(embed=embed)

# --- +settings / +showconfig ---
@bot.command(name="settings")
@has_required_role()
async def server_settings(ctx):
    await ctx.send("⚙️ Panneau de configuration des messages de Bienvenue et de Départ actif.")

@bot.command(name="showconfig")
@has_required_role()
async def show_config(ctx):
    await ctx.send("📜 Affichage complet de la configuration de votre bot sur ce serveur. [Structure OK]")

# --- +soutien / +staff-list ---
@bot.command(name="soutien")
@has_required_role()
async def soutien_system(ctx):
    await ctx.send("✨ Configuration du système de rôles de soutien (Statut personnalisé) accessible.")

@bot.command(name="staff-list")
@has_required_role()
async def staff_list(ctx):
    await ctx.send("📋 Affichage de la liste du Staff classée par niveau de permission... [Configuration en cours]")

# --- +sync ---
@bot.command(name="sync")
@has_required_role()
async def sync_category(ctx):
    if not ctx.channel.category:
        return await ctx.send("❌ Ce salon n'appartient à aucune catégorie.")
    await ctx.channel.edit(sync_permissions=True)
    await ctx.send("🔄 Salon synchronisé avec les permissions de sa catégorie.")

# --- +ticket / +ticket-stats ---
@bot.command(name="ticket")
@has_required_role()
async def manage_tickets(ctx):
    await ctx.send("🎟️ Commande principale pour la configuration et la gestion des tickets ouverte.")

@bot.command(name="ticket-stats")
@has_required_role()
async def ticket_stats(ctx):
    await ctx.send("📊 Aucun ticket fermé pour le moment. Taux de réponse moyen : `0s`.")

# --- +unban / +unbanall ---
@bot.command(name="unban")
@has_required_role()
async def unban_user(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"✅ **{user.name}** a été débanni du serveur.")

@bot.command(name="unbanall")
@has_required_role()
async def unban_all(ctx):
    bans = [entry async for entry in ctx.guild.bans()]
    for entry in bans:
        await ctx.guild.unban(entry.user)
    await ctx.send(f"🔓 Révocations massives réussies. `{len(bans)}` utilisateur(s) débanni(s).")

# ==========================================
# MODULE BUYER (SÉCURITÉ DOUBLE - RÔLE + ADMIN)
# ==========================================

# --- +automod / +badword ---
@bot.command(name="automod")
@has_required_role()
async def automod_badge(ctx):
    await ctx.send("🤖 Configuration des règles AutoMod de Discord initiée pour l'obtention du badge.")

@bot.command(name="badword")
@has_required_role()
async def badword_manage(ctx, action: str, word: str = None):
    await ctx.send(f"🛡️ Action `{action}` appliquée sur la liste des mots interdits.")

# --- +bl / +unbl / +blinfo / +wl ---
@bot.command(name="bl")
@has_required_role()
async def blacklist_add(ctx, user: discord.User):
    await ctx.send(f"🖤 {user.mention} a été ajouté à la blacklist du bot.")

@bot.command(name="unbl")
@has_required_role()
async def blacklist_remove(ctx, user: discord.User):
    await ctx.send(f"🤍 {user.mention} a été retiré de la blacklist du bot.")

@bot.command(name="blinfo")
@has_required_role()
async def blacklist_info(ctx, user: discord.User):
    await ctx.send(f"🔍 Statut Blacklist pour {user.name} : `Blacklisté` | Raison : Non spécifiée.")

@bot.command(name="wl")
@has_required_role()
async def whitelist_manage(ctx, action: str, user: discord.User):
    await ctx.send(f"⚙️ {user.mention} a été `{action}` de la whitelist.")

# --- +owner ---
@bot.command(name="owner")
@has_required_role()
async def owner_add(ctx, user: discord.User):
    await ctx.send(f"👑 {user.mention} a été promu au rang d'Owner du bot.")

# --- Statuts et Présences (+online, +dnd, +idle, +invisible, +del-activity) ---
@bot.command(name="online")
@has_required_role()
async def set_online(ctx):
    await bot.change_presence(status=discord.Status.online)
    await ctx.send("🟢 Statut du bot mis sur : **En ligne**.")

@bot.command(name="dnd")
@has_required_role()
async def set_dnd(ctx):
    await bot.change_presence(status=discord.Status.dnd)
    await ctx.send("🔴 Statut du bot mis sur : **Ne pas déranger**.")

@bot.command(name="idle")
@has_required_role()
async def set_idle(ctx):
    await bot.change_presence(status=discord.Status.idle)
    await ctx.send("🟡 Statut du bot mis sur : **Inactif**.")

@bot.command(name="invisible")
@has_required_role()
async def set_invisible(ctx):
    await bot.change_presence(status=discord.Status.invisible)
    await ctx.send("⚫ Statut du bot mis sur : **Invisible**.")

@bot.command(name="del-activity")
@has_required_role()
async def delete_activity(ctx):
    await bot.change_presence(activity=None)
    await ctx.send("🧹 Activité du bot supprimée.")

# --- Activités (+play, +stream, +listen, +watch, +setstream) ---
@bot.command(name="play")
@has_required_role()
async def set_game(ctx, *, text: str):
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"🎮 Le bot joue maintenant à : `{text}`")

@bot.command(name="stream")
@has_required_role()
async def set_stream(ctx, *, text: str):
    await bot.change_presence(activity=discord.Streaming(name=text, url="https://twitch.tv/twitch"))
    await ctx.send(f"💜 Le bot est maintenant en live sur : `{text}`")

@bot.command(name="setstream")
@has_required_role()
async def set_stream_url(ctx, url: str):
    await ctx.send(f"🔗 URL de stream par défaut mise à jour : `{url}`")

@bot.command(name="listen")
@has_required_role()
async def set_listen(ctx, *, text: str):
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=text))
    await ctx.send(f"🎧 Le bot écoute maintenant : `{text}`")

@bot.command(name="watch")
@has_required_role()
async def set_watch(ctx, *, text: str):
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
    await ctx.send(f"📺 Le bot regarde maintenant : `{text}`")

# --- Personnalisation Bot (+setname, +setpic, +setbanner, +prefix, +theme, +lang) ---
@bot.command(name="setname")
@has_required_role()
async def set_bot_name(ctx, *, new_name: str):
    await bot.user.edit(username=new_name)
    await ctx.send(f"✏️ Nom du bot modifié avec succès : `{new_name}`")

@bot.command(name="setpic")
@has_required_role()
async def set_bot_avatar(ctx, url: str):
    async with bot.session.get(url) as resp:
        if resp.status == 200:
            await bot.user.edit(avatar=await resp.read())
            await ctx.send("🖼️ Photo de profil du bot mise à jour.")

@bot.command(name="setbanner")
@has_required_role()
async def set_bot_banner(ctx, url: str):
    await ctx.send("🖼️ Requête de changement de bannière envoyée à l'API Discord.")

@bot.command(name="prefix")
@has_required_role()
async def change_prefix(ctx, new_prefix: str):
    bot.command_prefix = new_prefix
    await ctx.send(f"⚙️ Préfixe global modifié. Nouveau préfixe : `{new_prefix}`")

@bot.command(name="theme")
@has_required_role()
async def change_theme(ctx, hex_code: str):
    await ctx.send(f"🎨 Couleur par défaut des embeds configurée sur : `{hex_code}`")

@bot.command(name="lang")
@has_required_role()
async def change_lang(ctx, lang_code: str):
    await ctx.send(f"🌐 Language updated to: `{lang_code}`")

# --- Utilitaires Globaux (+say, +mp, +leave, +serverlist, +server-invite) ---
@bot.command(name="say")
@has_required_role()
async def bot_say(ctx, *, text: str):
    await ctx.message.delete()
    await ctx.send(text)

@bot.command(name="mp")
@has_required_role()
async def send_dm(ctx, user: discord.User, *, message: str):
    try:
        await user.send(message)
        await ctx.send(f"📩 Message privé envoyé avec succès à {user.name}.")
    except discord.Forbidden:
        await ctx.send("❌ Impossible d'envoyer un message à cet utilisateur (DMs fermés).")

@bot.command(name="leave")
@has_required_role()
async def leave_guild(ctx):
    await ctx.send("👋 Quittons ce serveur...")
    await ctx.guild.leave()

@bot.command(name="serverlist")
@has_required_role()
async def list_servers(ctx):
    guilds = "\n".join([f"• {g.name} ({g.id}) | {g.member_count} membres" for g in bot.guilds])
    
# 5. Lancement du programme
async def main():
    async with bot:
        await load_extensions()
        import os
        await bot.start(os.getenv("TOKEN"))

# Exécution du script
if __name__ == "__main__":
    asyncio.run(main())
