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
import traceback
import hashlib
from urllib.parse import urlsplit, urlunsplit
from urllib.parse import urlparse

# === LATIDO DEL BOT (Monitor anti-cuelgue) ===
ultimo_latido = time.time()

def monitor_actividad():
    while True:
        if time.time() - ultimo_latido > 180:
            try:
                enviar_telegram("⚠️ El bot dejó de latir. Posible cuelgue o apagado inesperado.")
            except:
                pass
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
LOCK_FILE = "bot.lock"
MAX_IDS = 10000

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
    "لوحات مزورة", "وثائق مزورة", "تزوير الوثائق", "تزوير",

    # ---- TERRORISMO ES ----
    "terrorismo","terrorista","terroristas","yihadismo","yihadista","yihadistas",
    "atentado","atentados","explosión","explosion","explosivo","explosivos",
    "célula","celula","célula terrorista","celula terrorista",
    "radicalización","radicalizacion","reclutamiento",
    "estado islámico","estado islamico","daesh","isis","al qaeda","aqmi",

    # ---- TERRORISMO FR ----
    "terrorisme","terroriste","terroristes",
    "djihadisme","djihadiste","djihadistes",
    "attentat","attentats","explosif","explosifs",
    "cellule terroriste","radicalisation","recrutement",
    "etat islamique","état islamique","daech","al qaida",

    # ---- TERRORISMO AR ----
    "إرهاب","ارهاب","إرهابي","إرهابية","تطرف",
    "جهاد","جهادي","تفجير","متفجرات",
    "خلية إرهابية","داعش","تنظيم الدولة","القاعدة",
]

COMBINACIONES_ESPECIALES = [
    ("véhicule", "volé"), ("véhicules", "volés"), ("voiture", "volée"), ("voitures", "volées"),
    ("moto", "volée"), ("motos", "volées"), ("plaque", "dupliquée"), ("plaques", "dupliquées"),
    ("document", "faux"), ("falsification", "documents"), ("مركبة", "مسروقة"), ("مركبات", "مسروقة"),
    ("سيارة", "مسروقة"), ("سيارات", "مسروقة"), ("دراجة", "نارية"), ("دراجات", "نارية"),
    ("لوحة", "مزورة"), ("لوحات", "مزورة"), ("وثائق", "مزورة"), ("تزوير", "الوثائق"),
    ("قارب", "موت"), ("حبوب", "مهلوسة"), ("حبوب", "مخدرة"),
    ("خلية","إرهابية"), ("célula","terrorista"), ("cellule","terroriste"),
]

COMBINACIONES_TRIPLES = [
    ("ministerio","interior","informe estadístico"),
    ("ministerio","interior","balance"),
    ("ministerio","interior","memorándum"),
    ("ministère","intérieur","rapport statistique"),
    ("ministère","intérieur","bilan"),
    ("ministère","intérieur","mémorandum"),
    ("وزارة","الداخلية","تقرير إحصائي"),
    ("وزارة","الداخلية","حصيلة"),
    ("وزارة","الداخلية","مذكرة"),
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
    "https://telquel.ma/feed/",
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
    "https://fr.le360.ma/rss", 
    "https://sport.le360.ma/rss", 
    "https://www.hespress.com/feed",
    "https://www.yabiladi.com/rss/news.xml",
    "https://www.hibapress.com/feed",
    "https://www.bladi.net/spip.php?page=backend", 
    "https://bladna24.ma/feed/",
    "https://tanjanews.com/feed",
    "https://presstetouan.com/feed", 
    "https://mobile.telquel.ma/feed",
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
    "https://almolahidjournal.com/feed/",
    "https://marrakechalaan.com/feed/",
    "https://fr.hibapress.com/feed/", 
    "https://sabahagadir.ma/feed/",
    "https://anbaarrakech.com/feed/",
    "https://k36.ma/feed",
    "https://ledesk.ma/feed",
    "https://lopinion.ma/feed",
    "https://www.alwatan.ma/feed",
    "https://www.akherkhabar.ma/feed",
    "https://www.akhbarona.com/feed",
    "https://telexpresse.com/feed",   
    "https://agadir24.info/feed",
    "https://tantan24.com/feed",
    "https://fesnews.net/feed",  
    
    # CEUTA / MELILLA
    "https://elfarodeceuta.es/feed",
    "https://elfarodeceuta.es/sucesos-seguridad/feed",
    "https://www.ceutaactualidad.com/rss/",
    "https://www.ceutaldia.com/rss/",
    "https://www.melillaactualidad.com/rss/",
]

print(f"Total de feeds: {len(RSS_FEEDS)}")

for url in RSS_FEEDS:
    print(f"Feed cargado: {url}")
    
# === UTILIDADES ===
def normalizar_titulo(t: str) -> str:
    if not t:
        return ""
    t = t.lower().strip()
    t = re.sub(r"[^a-z0-9áéíóúüñçàèìòùâêîôûäëïöü\s-]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def dominio_de_feed(feed_url: str) -> str:
    try:
        return urlparse(feed_url).netloc.lower()
    except:
        return (feed_url or "").lower()

def uid_por_medio(feed_url: str, link: str, title: str) -> str:
    dom = dominio_de_feed(feed_url)
    link_norm = normalizar_url(link)

    base = link_norm or normalizar_titulo(title)
    if not base:
        return ""
    return "M_" + hashlib.sha1(f"{dom}|{base}".encode("utf-8", errors="ignore")).hexdigest()

def normalizar_url(url: str) -> str:
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
        clean = parts._replace(query="", fragment="")
        scheme = "https" if clean.scheme in ("http", "https") else clean.scheme
        clean = clean._replace(scheme=scheme)
        u = urlunsplit(clean).rstrip("/")
        return u
    except:
        return url.strip()

def construir_uid(entry) -> str:
    link = normalizar_url(entry.get("link", ""))
    guid = entry.get("id") or entry.get("guid") or ""
    published = entry.get("published", "") or entry.get("updated", "") or ""
    title = (entry.get("title", "") or "").strip().lower()

    base = "|".join([guid.strip(), link, published.strip(), title])
    if not base.strip():
        return ""
    return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()

def adquirir_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                pid_str = f.read().strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                os.kill(pid, 0)  # comprueba si existe el proceso
                print("⚠️ Ya hay una instancia del bot ejecutándose. Salgo.")
                sys.exit(0)
        except:
            pass

    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

def cargar_ids_notificados():
    if not os.path.exists(HISTORIAL_FILE):
        return set()
    with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def guardar_id_notificado(unique_id):
    notificados.add(unique_id)

    try:
        ids = list(notificados)

        # Limita tamaño (evita crecimiento infinito)
        if len(ids) > MAX_IDS:
            ids = ids[-MAX_IDS:]

        # Reescribe el archivo completo (más estable que append)
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            for x in ids:
                f.write(x + "\n")

    except Exception as e:
        log_event(f"❌ Error guardando historial: {e}")

def log_event(text):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] {text}\n")
    except Exception:
        print("LOG ERROR:", text)

def contiene_palabra_clave(texto):
    for palabra in GENERAL_KEYWORDS:
        if re.search(rf'\b{re.escape(palabra)}\b', texto, re.IGNORECASE):
            return True

    for p1, p2 in COMBINACIONES_ESPECIALES:
        if (re.search(rf'\b{re.escape(p1)}\b', texto, re.IGNORECASE) and
            re.search(rf'\b{re.escape(p2)}\b', texto, re.IGNORECASE)):
            return True

    for p1, p2, p3 in COMBINACIONES_TRIPLES:
        if (re.search(rf'\b{re.escape(p1)}\b', texto, re.IGNORECASE) and
            re.search(rf'\b{re.escape(p2)}\b', texto, re.IGNORECASE) and
            re.search(rf'\b{re.escape(p3)}\b', texto, re.IGNORECASE)):
            return True

    return False

def enviar_telegram(mensaje):
    try:
        for chat_id in CHAT_IDS:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
            r = requests.post(url, data=data, timeout=20)
            if not r.ok:
                log_event(f"❌ Error al enviar a {chat_id}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log_event(f"❌ Error general al enviar mensaje: {e}")

def revisar_rss():
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:30]:
                link = entry.get("link", "")
                title = entry.get("title", "")
                summary = entry.get("summary", "")

                # Normaliza link y crea UID por medio
                link = normalizar_url(link) or link
                uid_medio = uid_por_medio(url, link, title)

                # Si no hay uid, pasa
                if not uid_medio:
                    continue

                # Si ya está notificado, pasa
                if uid_medio in notificados:
                    continue

                texto = f"{title} {summary}"

                if contiene_palabra_clave(texto):
                    mensaje = f"📰 <b>{title}</b>\n🔗 {link}"
                    enviar_telegram(mensaje)
                    guardar_id_notificado(uid_medio)
                    log_event(f"✅ Enviada noticia: {title}")

        except Exception as e:
            log_event(f"⚠️ Error en feed {url}: {e}")

def resumen_diario_ya_enviado():
    if not os.path.exists(ULTIMO_RESUMEN_FILE):
        return False
    with open(ULTIMO_RESUMEN_FILE, encoding='utf-8') as f:
        return f.read().strip() == datetime.now().strftime("%Y-%m-%d")

def marcar_resumen_enviado():
    with open(ULTIMO_RESUMEN_FILE, "w", encoding='utf-8') as f:
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
        texto += "\n".join([f"• {t}" for t in resumenes[:50]])
        if len(resumenes) > 50:
            texto += f"\n\n(+{len(resumenes)-50} más)"
    else:
        texto += "No se enviaron noticias hoy."

    enviar_telegram(texto)
    marcar_resumen_enviado()

# === FLASK KEEP-ALIVE ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo 🚀"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)

def keep_alive():
    Thread(target=run).start()

# === SEÑALES ===
def manejar_salida_graciosa(signum, frame):
    try:
        enviar_telegram("⚠️ El bot de noticias se ha detenido (señal recibida)")
    except:
        pass
    log_event("⚠️ Bot detenido por señal")
    sys.exit(0)

signal.signal(signal.SIGINT, manejar_salida_graciosa)
signal.signal(signal.SIGTERM, manejar_salida_graciosa)

# === INICIO ===
adquirir_lock()
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
    traceback.print_exc()
    msg = f"❌ Error:\n{e}"
    enviar_telegram(msg)
    log_event(msg)

finally:
    enviar_telegram("⚠️ Bot desconectado")
    log_event("⚠️ Bot desconectado (bloque finally)")
