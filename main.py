from flask import Flask
from threading import Thread
import requests
import feedparser
import time
import re
import os
import signal
import sys
from datetime import datetime

# === LATIDO DEL BOT (Monitor anti-cuelgue) ===
ultimo_latido = time.time()

def monitor_actividad():
    while True:
        if time.time() - ultimo_latido > 180:
            enviar_telegram("⚠️ El bot dejó de latir. Posible cuelgue o apagado inesperado.")
            log_event("❗ Latido perdido. Forzando salida.")
            os._exit(1)
        time.sleep(60)

Thread(target=monitor_actividad, daemon=True).start()

# === CONFIGURACIÓN ===
TELEGRAM_TOKEN = '7878852704:AAEHZclqxGxFclcVgwRD2gsIKpCtVrZpEIs'
CHAT_IDS = ['396759277', '-1002681283803']
HISTORIAL_FILE = "notificados.txt"
LOG_FILE = "registro.log"
ULTIMO_RESUMEN_FILE = "ultimo_resumen.txt"

# === PALABRAS CLAVE ===
GENERAL_KEYWORDS = [
    "droga", "drogas", "narcotráfico", "tráfico de drogas", "narcos", "cocaína", "cocaina",
    "hachís", "hachis", "heroína", "heroina", "lsd", "éxtasis", "extasis", "mdma", "ketamina",
    "alucinógenos", "psicotrópicos", "estupefacientes", "sustancias ilícitas", "sustancias prohibidas",
    "contrabando", "mercancía ilegal", "tabaco ilegal", "cajetillas", "cigarrillos",
    "inmigración ilegal", "inmigración irregular", "migrantes ilegales", "patera", "cayuco", "frontera sur",
    "saltos de valla", "vehículo robado", "vehículos robados", "coche robado", "coches robados",
    "moto robada", "motos robadas", "matrícula falsa", "matrículas falsas", "matrículas duplicadas",
    "documento falso", "documentación falsa", "papeles falsos", "falsificación", "fraude documental",
    "trafic de drogue", "drogue", "drogues", "cocaïne", "hachisch", "héroïne", "psychotropes",
    "hallucinogènes", "stupéfiants", "substances illicites", "ecstasy", "lsd", "mdma", "kétamine",
    "contrebande", "tabac de contrebande", "cigarettes", "marchandises illégales", "immigration illégale",
    "immigration clandestine", "migrants illégaux", "passeur", "passeurs", "bateau de migrants", "barque",
    "franchissement illégal", "véhicule volé", "véhicules volés", "voiture volée", "voitures volées",
    "moto volée", "motos volées", "plaque falsifiée", "plaques falsifiées", "plaque dupliquée",
    "plaques dupliquées", "faux documents", "falsification de documents", "fraude documentaire",
    "مخدرات", "مخدر", "كوكايين", "حشيش", "هيروين", "حبوب مهلوسة", "مؤثرات عقلية", "حبوب",
    "مواد مخدرة", "أقراص مخدرة", "أقراص مهلوسة", "التهريب", "السجائر المهربة", "سجائر مهربة",
    "تبغ مهرب", "بضائع مهربة", "ممنوعات", "الهجرة السرية", "الهجرة غير الشرعية", "الهجرة غير النظامية",
    "مهاجرين سريين", "قارب", "قوارب الموت", "مهاجرين غير شرعيين", "سيارة مسروقة", "سيارات مسروقة",
    "مركبة مسروقة", "مركبات مسروقة", "دراجة نارية مسروقة", "دراجات نارية مسروقة", "لوحة مزورة",
    "لوحات مزورة", "وثائق مزورة", "تزوير الوثائق", "تزوير"
]

COMBINACIONES_ESPECIALES = [
    ("véhicule", "volé"), ("véhicules", "volés"), ("voiture", "volée"), ("voitures", "volées"),
    ("moto", "volée"), ("motos", "volées"), ("plaque", "dupliquée"), ("plaques", "dupliquées"),
    ("document", "faux"), ("falsification", "documents"), ("مركبة", "مسروقة"), ("مركبات", "مسروقة"),
    ("سيارة", "مسروقة"), ("سيارات", "مسروقة"), ("دراجة", "نارية"), ("دراجات", "نارية"),
    ("لوحة", "مزورة"), ("لوحات", "مزورة"), ("وثائق", "مزورة"), ("تزوير", "الوثائق"),
    ("قارب", "موت"), ("حبوب", "مهلوسة"), ("حبوب", "مخدرة")
]

# === FUENTES RSS ===
RSS_FEEDS = [
    "https://fr.le360.ma/rss",
    "https://sport.le360.ma/rss",
    "https://www.hespress.com/feed",
    "https://www.yabiladi.com/rss/news.xml",
    "https://www.hibapress.com/feed",
    "https://www.bladi.net/spip.php?page=backend",
    "https://bladna24.ma/feed/",
    "https://tanjanews.com/feed",
    "https://presstetouan.com/feed",
    "https://telquel.ma/feed/",  # Usamos la versión principal
    "https://casapress.net/feed",
    "https://lematin.ma/rss",
    "https://aujourdhui.ma/feed",
    "https://albayane.press.ma/feed",
    "https://www.chtoukapress.com/feed/",
    "https://marochebdo.press.ma/feed",
    "https://lnt.ma/feed",
    "https://alaoual.com/feed",
    "https://lereporter.ma/feed",
    "https://medias24.com/feed/",
    "https://www.barlamane.com/feed",
    "https://www.rue20.com/feed/",
    "https://www.assahifa.com/feed",
    "https://alyaoum24.com/feed",
    "https://www.moroccoworldnews.com/feed/",
    "https://www.goud.ma/feed",
    "https://kech24.com/feed",
    "https://www.nadorcity.com/xml/syndication.rss",
    "https://www.febrayer.com/feed",
    "https://quid.ma/rss.xml",
    "https://www.lavieeco.com/feed/",
    "http://www.leconomiste.com/categorie/economie/feed",
    "http://www.almassae.press.ma/rss",
    "http://assabah.ma/feed/",
    "https://almolahidjournal.com/feed/",
    "https://marrakechalaan.com/feed/",
    "https://fr.hibapress.com/feed/", 
    "https://sabahagadir.ma/feed/",
    "https://anbaarrakech.com/feed/",
    
]

# === FUNCIONES UTILITARIAS ===

def cargar_ids_notificados():
    if not os.path.exists(HISTORIAL_FILE):
        return set()
    with open(HISTORIAL_FILE, 'r') as f:
        return set(line.strip() for line in f)

def guardar_id_notificado(unique_id):
    with open(HISTORIAL_FILE, 'a') as f:
        f.write(unique_id + "\n")
    notificados.add(unique_id)

def log_event(text):
    with open(LOG_FILE, 'a', encoding='utf-8') as log:
        log.write(f"[{datetime.now()}] {text}\n")

def contiene_palabra_clave(texto):
    for palabra in GENERAL_KEYWORDS:
        if re.search(rf'\b{re.escape(palabra)}\b', texto, re.IGNORECASE):
            return True
    for p1, p2 in COMBINACIONES_ESPECIALES:
        if re.search(rf'\b{re.escape(p1)}\b', texto, re.IGNORECASE) and re.search(rf'\b{re.escape(p2)}\b', texto, re.IGNORECASE):
            return True
    return False

def texto_ya_en_espanol(texto):
    comunes = ["el", "la", "de", "que", "y", "en", "los", "las"]
    return sum(1 for p in comunes if p in texto.lower()) >= 3

def traducir_texto(texto, target='es'):
    return None


def enviar_telegram(mensaje):
    try:
        for chat_id in CHAT_IDS:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
            response = requests.post(url, data=data)
            if not response.ok:
                log_event(f"❌ Error al enviar a {chat_id}: {response.text}")
    except Exception as e:
        log_event(f"❌ Error general al enviar mensaje: {e}")


# === FUNCIONES PRINCIPALES ===

def revisar_rss():
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)

            if not hasattr(feed, "entries") or not feed.entries:
                log_event(f"⚠️ Feed sin entradas o inválido: {url}")
                continue

            for entry in feed.entries:
                link = entry.get("link", "")
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                uid = link or title

                if uid in notificados:
                    continue

                texto = f"{title} {summary}"

                if contiene_palabra_clave(texto):
                    if not texto_ya_en_espanol(texto):
                        traduccion = traducir_texto(texto)
                        mensaje = (
                            f"📰 <b>{title}</b>\n🌍 <i>{traduccion}</i>\n🔗 {link}"
                            if traduccion else f"📰 <b>{title}</b>\n🔗 {link}"
                        )
                    else:
                        mensaje = f"📰 <b>{title}</b>\n🔗 {link}"

                    enviar_telegram(mensaje)
                    guardar_id_notificado(uid)
                    log_event(f"✅ Enviada noticia: {title}")

        except Exception as e:
            log_event(f"❌ Error al procesar feed {url}:\n{e}")
            enviar_telegram(f"❌ Error al procesar feed:\n{url}\n{e}")
            continue


def resumen_diario_ya_enviado():
    if not os.path.exists(ULTIMO_RESUMEN_FILE):
        return False
    with open(ULTIMO_RESUMEN_FILE) as f:
        return f.read().strip() == datetime.now().strftime("%Y-%m-%d")

def marcar_resumen_enviado():
    with open(ULTIMO_RESUMEN_FILE, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))

def enviar_resumen_diario():
    if resumen_diario_ya_enviado():
        return

    hoy = datetime.now().strftime("%Y-%m-%d")
    resumenes = []

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for linea in f:
                if hoy in linea and "✅ Enviada noticia:" in linea:
                    partes = linea.strip().split("✅ Enviada noticia: ")
                    if len(partes) > 1:
                        resumenes.append(partes[1])

    texto = f"🗞️ <b>Resumen diario ({hoy})</b>\n\n"
    if resumenes:
        texto += f"✅ {len(resumenes)} noticias enviadas hoy:\n"
        texto += "\n".join([f"• {t}" for t in resumenes])
    else:
        texto += "No se enviaron noticias hoy."

    enviar_telegram(texto)
    marcar_resumen_enviado()

# === FLASK KEEP-ALIVE ===

app = Flask('')

@app.route('/')
def home():
    return "Bot activo 🚀"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)



def keep_alive():
    Thread(target=run).start()

# === MANEJO DE SEÑALES ===

def manejar_salida_graciosa(signum, frame):
    enviar_telegram("⚠️ El bot de noticias se ha detenido (señal recibida)")
    log_event("⚠️ Bot detenido por señal")
    sys.exit(0)

signal.signal(signal.SIGINT, manejar_salida_graciosa)
signal.signal(signal.SIGTERM, manejar_salida_graciosa)

# === INICIO DEL BOT ===

notificados = cargar_ids_notificados()
keep_alive()

print("🟢 Bot de noticias iniciado...")
log_event("🟢 Bot de noticias iniciado")
enviar_telegram("✅ El bot de noticias ha sido iniciado correctamente 🚀")

try:
    while True:
        ultimo_latido = time.time()
        revisar_rss()
        if datetime.now().strftime("%H:%M") == "23:55":
            enviar_resumen_diario()
        time.sleep(60)

except Exception as e:
    msg = f"❌ Error:\n{e}"
    enviar_telegram(msg)
    log_event(msg)

finally:
    enviar_telegram("⚠️ Bot desconectado")
log_event("⚠️ Bot desconectado (bloque finally)")
