"""
Elyndra la Receptionist — index.py
------------------------------------
Punto d'ingresso del bot. Invia, ogni 8 ore, un messaggio (embed) nel
canale scelto per annunciare che le missioni della Gilda di Osteria si
sono resettate.

Funzioni:
  - Invio automatico ogni 8 ore in un canale configurabile
  - Embed "a tema elfico" con titolo, testo, colore e immagine
  - /imposta_canale   -> scegli in quale canale scrivere
  - /modifica_messaggio -> cambia il testo del messaggio direttamente da Discord
  - /imposta_immagine   -> cambia l'immagine (via URL) direttamente da Discord
  - /invia_ora         -> invia subito il messaggio (utile per testare)
  - /anteprima         -> mostra l'embed attuale senza inviarlo nel canale pubblico

L'immagine locale di Elyndra va messa in: assets/elyndra.png
(puoi sostituirla in qualsiasi momento con un'altra immagine, basta
mantenere lo stesso nome file, oppure impostarne una via URL col comando
/imposta_immagine).
"""

import os
import json
import discord
import aiohttp
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
# Render imposta automaticamente questa variabile con l'URL pubblico del
# servizio (es. https://elyndra-bot.onrender.com). Se per qualche motivo
# non fosse presente, puoi impostarla tu a mano su Render con lo stesso nome.
KEEP_ALIVE_URL = os.getenv("RENDER_EXTERNAL_URL")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
LOCAL_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "assets", "elyndra.png")

DEFAULT_CONFIG = {
    "channel_id": 1546608761228238908,
    "title": "📜 Le missioni della Gilda si sono rinnovate!",
    "description": (
        "\n\n"
        "Salve avventurieri! Le bacheche della **Gilda di Osteria** sono state "
        "appena aggiornate: le vecchie missioni sono state archiviate e "
        "**nuovi incarichi vi attendono** presso lo sportello.\n\n"
        "Fatevi avanti prima che i migliori vengano presi da altri! ✨"
    ),
    "footer": "Elyndra la Receptionist • Gilda di Osteria",
    "color": 0xB388FF,  # viola/lilla elfico
    "image_url": "https://cdn.discordapp.com/attachments/1523058897714413698/1546608132682424340/26b49355-7328-4c44-95d6-9c0da7bf5b99_-_Modificata.png?ex=6aa06691&is=6a9f1511&hm=5d3a78984866185a73229380708d599fd8d1405b370c778a51dab78bceef3d36&";  # se impostata, ha priorità sull'immagine locale
}


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # assicura che eventuali nuove chiavi di default esistano sempre
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


config = load_config()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


def build_embed() -> tuple[discord.Embed, discord.File | None]:
    """Costruisce l'embed da inviare, e l'eventuale file immagine locale da allegare."""
    embed = discord.Embed(
        title=config["title"],
        description=config["description"],
        color=config["color"],
    )
    embed.set_author(name="Elyndra la Receptionist")
    embed.set_footer(text=config["footer"])

    file_to_send = None
    if config.get("image_url"):
        embed.set_image(url=config["image_url"])
    elif os.path.exists(LOCAL_IMAGE_PATH):
        file_to_send = discord.File(LOCAL_IMAGE_PATH, filename="elyndra.png")
        embed.set_image(url="attachment://elyndra.png")

    return embed, file_to_send


@bot.event
async def on_ready():
    print(f"✅ Connessa come {bot.user} (Elyndra la Receptionist)")
    try:
        synced = await bot.tree.sync()
        print(f"🔧 Sincronizzati {len(synced)} comandi slash")
    except Exception as e:
        print(f"Errore sync comandi: {e}")

    if not invio_periodico.is_running():
        invio_periodico.start()

    if not keep_alive_ping.is_running():
        keep_alive_ping.start()


@tasks.loop(hours=8)
async def invio_periodico():
    channel_id = config.get("channel_id")
    if not channel_id:
        print("⚠️ Nessun canale impostato: usa /imposta_canale su Discord.")
        return

    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception as e:
            print(f"⚠️ Impossibile trovare il canale {channel_id}: {e}")
            return

    embed, file_to_send = build_embed()
    if file_to_send:
        await channel.send(embed=embed, file=file_to_send)
    else:
        await channel.send(embed=embed)


@invio_periodico.before_loop
async def before_invio_periodico():
    await bot.wait_until_ready()


@tasks.loop(minutes=14)
async def keep_alive_ping():
    """Si auto-chiama ogni 14 minuti per evitare che Render metta in pausa
    il servizio gratuito per inattività (il limite di Render è 15 minuti)."""
    if not KEEP_ALIVE_URL:
        return  # in locale, o se la variabile non è impostata, non fa nulla
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(KEEP_ALIVE_URL) as resp:
                print(f"🔁 Keep-alive ping -> status {resp.status}")
    except Exception as e:
        print(f"⚠️ Keep-alive ping fallito: {e}")


@keep_alive_ping.before_loop
async def before_keep_alive_ping():
    await bot.wait_until_ready()


# ---------------------- COMANDI SLASH ----------------------

@bot.tree.command(name="imposta_canale", description="Imposta il canale dove Elyndra invierà gli annunci delle missioni")
@app_commands.describe(canale="Il canale in cui inviare il messaggio ogni 8 ore")
@app_commands.checks.has_permissions(manage_guild=True)
async def imposta_canale(interaction: discord.Interaction, canale: discord.TextChannel):
    config["channel_id"] = canale.id
    save_config(config)
    await interaction.response.send_message(
        f"✅ Da ora Elyndra invierà i suoi annunci in {canale.mention} ogni 8 ore.",
        ephemeral=True,
    )


@bot.tree.command(name="modifica_messaggio", description="Cambia il testo del messaggio delle missioni")
@app_commands.describe(
    titolo="Nuovo titolo dell'embed (lascia vuoto per non modificarlo)",
    testo="Nuovo testo/descrizione dell'embed (lascia vuoto per non modificarlo)",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def modifica_messaggio(
    interaction: discord.Interaction,
    titolo: str | None = None,
    testo: str | None = None,
):
    if titolo is None and testo is None:
        await interaction.response.send_message(
            "⚠️ Devi specificare almeno il titolo o il testo da modificare.",
            ephemeral=True,
        )
        return

    if titolo:
        config["title"] = titolo
    if testo:
        config["description"] = testo
    save_config(config)

    embed, file_to_send = build_embed()
    if file_to_send:
        await interaction.response.send_message(
            "✅ Messaggio aggiornato! Ecco l'anteprima:", embed=embed, file=file_to_send, ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "✅ Messaggio aggiornato! Ecco l'anteprima:", embed=embed, ephemeral=True
        )


@bot.tree.command(name="imposta_immagine", description="Imposta l'immagine di Elyndra da un URL")
@app_commands.describe(url="Link diretto all'immagine (es. https://.../immagine.png). Scrivi 'reset' per tornare all'immagine locale.")
@app_commands.checks.has_permissions(manage_guild=True)
async def imposta_immagine(interaction: discord.Interaction, url: str):
    if url.lower() == "reset":
        config["image_url"] = None
        save_config(config)
        await interaction.response.send_message(
            "✅ Immagine ripristinata a quella locale (assets/elyndra.png).",
            ephemeral=True,
        )
        return

    config["image_url"] = url
    save_config(config)
    embed, _ = build_embed()
    await interaction.response.send_message(
        "✅ Immagine aggiornata! Ecco l'anteprima:", embed=embed, ephemeral=True
    )


@bot.tree.command(name="invia_ora", description="Invia subito il messaggio delle missioni nel canale impostato")
@app_commands.checks.has_permissions(manage_guild=True)
async def invia_ora(interaction: discord.Interaction):
    channel_id = config.get("channel_id")
    if not channel_id:
        await interaction.response.send_message(
            "⚠️ Nessun canale impostato. Usa prima /imposta_canale.", ephemeral=True
        )
        return

    channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
    embed, file_to_send = build_embed()
    if file_to_send:
        await channel.send(embed=embed, file=file_to_send)
    else:
        await channel.send(embed=embed)

    await interaction.response.send_message("✅ Messaggio inviato!", ephemeral=True)


@bot.tree.command(name="anteprima", description="Mostra un'anteprima privata del messaggio attuale")
async def anteprima(interaction: discord.Interaction):
    embed, file_to_send = build_embed()
    if file_to_send:
        await interaction.response.send_message(embed=embed, file=file_to_send, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


@imposta_canale.error
@modifica_messaggio.error
@imposta_immagine.error
@invia_ora.error
async def permesso_negato(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "⛔ Devi avere il permesso 'Gestisci Server' per usare questo comando.",
            ephemeral=True,
        )
    else:
        raise error


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit(
            "❌ Token mancante! Crea un file .env con dentro: DISCORD_TOKEN=il_tuo_token"
        )
    keep_alive()  # avvia il piccolo web server per Render
    bot.run(TOKEN)
