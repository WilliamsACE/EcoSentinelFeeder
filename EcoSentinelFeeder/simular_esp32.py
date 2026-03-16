"""
╔══════════════════════════════════════════════════════╗
║   SIMULADOR ESP32 — EcoSentinel Feeder               ║
║   Simula el envío de datos desde el feeder           ║
║   al servidor Django para probar los endpoints.      ║
╚══════════════════════════════════════════════════════╝
USO:
    python simular_esp32.py

REQUISITOS:
    pip install requests

FOTOS:
    Coloca imágenes en la carpeta definida en PHOTOS_DIR.
    Se enviarán aleatoriamente junto con cada detección.
    Formatos soportados: jpg, jpeg, png, webp, gif
    Si la carpeta está vacía o no existe, las detecciones
    se envían igual pero sin foto adjunta.

    Estructura sugerida:
        fotos_esp32/
        ├── perro_01.jpg
        ├── gato_01.jpg
        ├── alerta_01.jpg
        └── ...
"""

import requests
import random
import time
import os
import glob
from datetime import datetime
from pathlib import Path

# ── CONFIGURACIÓN ──────────────────────────────────────────────────
SERVER     = 'http://127.0.0.1:8000'
TOKEN      = 'YeahPerdonenKamehameha'
FEEDER_ID  = 'ESF-001'

# Carpeta donde están las fotos a enviar con cada detección
PHOTOS_DIR = 'fotos_esp32'

# Extensiones de imagen aceptadas
PHOTO_EXTS = ('*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif')

G  = '\033[92m'; R  = '\033[91m'; Y  = '\033[93m'
B  = '\033[94m'; W  = '\033[97m'; M  = '\033[95m'; RE = '\033[0m'
# ───────────────────────────────────────────────────────────────────


def log(color, icono, mensaje):
    hora = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{hora}] {icono}  {mensaje}{RE}")


# ── UTILIDADES DE FOTOS ────────────────────────────────────────────

def listar_fotos():
    """Devuelve una lista con todas las imágenes encontradas en PHOTOS_DIR."""
    fotos = []
    carpeta = Path(PHOTOS_DIR)
    if not carpeta.exists():
        return fotos
    for ext in PHOTO_EXTS:
        fotos.extend(carpeta.glob(ext))
        fotos.extend(carpeta.glob(ext.upper()))  # también mayúsculas (.JPG, .PNG…)
    return sorted(set(fotos))


def elegir_foto_aleatoria():
    """Retorna una ruta aleatoria de la carpeta, o None si no hay fotos."""
    fotos = listar_fotos()
    return random.choice(fotos) if fotos else None


def elegir_foto_por_especie(species):
    """
    Intenta encontrar una foto cuyo nombre contenga el nombre de la especie.
    Si no hay coincidencia, elige una foto aleatoria de la carpeta.
    """
    fotos = listar_fotos()
    if not fotos:
        return None
    coincidencias = [f for f in fotos if species.lower() in f.stem.lower()]
    if coincidencias:
        return random.choice(coincidencias)
    return random.choice(fotos)


def _mime_type(ruta: Path) -> str:
    ext = ruta.suffix.lower()
    return {
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png':  'image/png',
        '.webp': 'image/webp',
        '.gif':  'image/gif',
    }.get(ext, 'application/octet-stream')


# ── ENDPOINTS ─────────────────────────────────────────────────────

def enviar_status(battery, food_dog, food_cat, water):
    """POST /api/feeder/status/"""
    try:
        res = requests.post(f'{SERVER}/api/feeder/status/', json={
            'feeder_id': FEEDER_ID, 'token': TOKEN,
            'battery': battery, 'food_dog': food_dog,
            'food_cat': food_cat, 'water': water,
        }, timeout=5)
        if res.status_code == 200:
            log(G, '📡', f'Status → estado:{res.json().get("status","?")}')
            log(W, '   ', f'🔋 {battery}%  🐕 {food_dog}%  🐈 {food_cat}%  💧 {water}%')
        elif res.status_code == 401: log(R, '🔒', 'Token incorrecto')
        elif res.status_code == 404: log(R, '❓', f'Feeder "{FEEDER_ID}" no existe')
        else: log(R, '❌', f'HTTP {res.status_code}: {res.text}')
    except requests.exceptions.ConnectionError:
        log(R, '🔌', f'Sin conexión a {SERVER}')
    except Exception as e:
        log(R, '💥', str(e))


def enviar_deteccion(species, grams, confidence, foto_path=None):
    """
    POST /api/feeder/detection/
    Si foto_path es una ruta válida, la adjunta como multipart/form-data.
    Si no hay foto, envía JSON normal (comportamiento original).
    """
    EMOJI = {'perro': '🐕', 'gato': '🐈', 'alerta': '⚠️'}

    payload = {
        'feeder_id':  FEEDER_ID,
        'token':      TOKEN,
        'species':    species,
        'grams':      grams,
        'confidence': confidence,
    }

    try:
        # ── Con foto ────────────────────────────────────────────
        if foto_path and Path(foto_path).is_file():
            ruta = Path(foto_path)
            mime = _mime_type(ruta)
            with open(ruta, 'rb') as f:
                res = requests.post(
                    f'{SERVER}/api/feeder/detection/',
                    data=payload,
                    files={'photo': (ruta.name, f, mime)},
                    timeout=10,
                )
            foto_label = f' 📷 {ruta.name}'
        # ── Sin foto (JSON) ─────────────────────────────────────
        else:
            res = requests.post(
                f'{SERVER}/api/feeder/detection/',
                json=payload,
                timeout=5,
            )
            foto_label = ''

        if res.status_code == 200:
            log(G, EMOJI.get(species, '?'),
                f'Detección → {species} · {grams}g · {confidence}%{foto_label}')
        elif res.status_code == 401: log(R, '🔒', 'Token incorrecto')
        elif res.status_code == 404: log(R, '❓', 'Feeder no encontrado')
        else: log(R, '❌', f'HTTP {res.status_code}: {res.text}')

    except requests.exceptions.ConnectionError:
        log(R, '🔌', f'Sin conexión a {SERVER}')
    except Exception as e:
        log(R, '💥', str(e))


def enviar_alerta(tipo, titulo, descripcion):
    """
    POST /api/feeder/alert/
    tipo → 'danger' | 'warn' | 'ok'
    """
    EMOJI_TIPO = {'danger': '🔴', 'warn': '🟡', 'ok': '🟢'}
    try:
        res = requests.post(f'{SERVER}/api/feeder/alert/', json={
            'feeder_id':   FEEDER_ID,
            'token':       TOKEN,
            'type':        tipo,
            'title':       titulo,
            'description': descripcion,
            'time':        datetime.now().strftime('%H:%M'),
            'location':    'Del Valle · CDMX',
        }, timeout=5)
        if res.status_code == 200:
            log(M, EMOJI_TIPO.get(tipo, '🔔'), f'Alerta enviada → [{tipo.upper()}] {titulo}')
        elif res.status_code == 401: log(R, '🔒', 'Token incorrecto')
        elif res.status_code == 404: log(R, '❓', 'Feeder no encontrado')
        else: log(R, '❌', f'HTTP {res.status_code}: {res.text}')
    except requests.exceptions.ConnectionError:
        log(R, '🔌', f'Sin conexión a {SERVER}')
    except Exception as e:
        log(R, '💥', str(e))


def verificar_endpoints():
    log(Y, '🔍', 'Verificando /api/dashboard/ ...')
    try:
        res = requests.get(f'{SERVER}/api/dashboard/', timeout=5)
        if res.status_code == 200:
            fs = res.json().get('feeders', [])
            log(G, '✅', f'dashboard OK — {len(fs)} feeder(s)')
            for f in fs:
                log(W, '   ', f'  → {f["id"]} {f["name"]} | {f["status"]} | bat:{f["battery"]}%')
        else: log(R, '❌', f'HTTP {res.status_code}')
    except: log(R, '🔌', 'Sin conexión')

    log(Y, '🔍', 'Verificando /api/history/ ...')
    try:
        res = requests.get(f'{SERVER}/api/history/?limit=5', timeout=5)
        if res.status_code == 200:
            evs = res.json().get('events', [])
            log(G, '✅', f'history OK — {len(evs)} evento(s)')
            for e in evs:
                log(W, '   ', f'  [{e["time"]}] {e["feederId"]} {e["emoji"]} {e["label"]} {e["grams"]}g {e["confidence"]}%')
        else: log(R, '❌', f'HTTP {res.status_code}')
    except: log(R, '🔌', 'Sin conexión')


def _info_fotos():
    """Imprime un resumen de las fotos disponibles en PHOTOS_DIR."""
    fotos = listar_fotos()
    carpeta = Path(PHOTOS_DIR)
    if not carpeta.exists():
        log(Y, '📁', f'Carpeta "{PHOTOS_DIR}" no encontrada — se creará si envías fotos')
        log(W, '   ', f'Crea la carpeta y agrega imágenes: {carpeta.resolve()}')
    elif not fotos:
        log(Y, '📂', f'Carpeta "{PHOTOS_DIR}" vacía — detecciones se enviarán sin foto')
    else:
        log(G, '📷', f'{len(fotos)} foto(s) disponibles en "{PHOTOS_DIR}":')
        for f in fotos[:8]:
            size_kb = f.stat().st_size // 1024
            log(W, '   ', f'  {f.name}  ({size_kb} KB)')
        if len(fotos) > 8:
            log(W, '   ', f'  … y {len(fotos) - 8} más')


# ══════════════════════════════════════════════════════════════
#  MODO 1 — Simulación completa (una sola pasada)
# ══════════════════════════════════════════════════════════════

def simulacion_completa():
    print(f'\n{B}{"═"*55}')
    print(f'   SIMULACIÓN COMPLETA — EcoSentinel Feeder')
    print(f'{"═"*55}{RE}\n')

    _info_fotos()
    print()
    verificar_endpoints()
    print()

    log(Y, '📉', 'Status con niveles bajando (5 envíos)...')
    bat, dog, cat, water = 80, 75, 70, 90
    for i in range(1, 6):
        log(B, f'#{i}', 'Enviando status...')
        enviar_status(bat, dog, cat, water)
        bat   = max(0, bat   - random.randint(1, 4))
        dog   = max(0, dog   - random.randint(3, 8))
        cat   = max(0, cat   - random.randint(2, 6))
        water = max(0, water - random.randint(1, 3))
        time.sleep(1)

    print()
    log(Y, '🐾', 'Detecciones con fotos (10 envíos)...')
    detecciones = [
        ('perro', 85, random.randint(88, 99)),
        ('gato',  60, random.randint(85, 98)),
        ('perro', 85, random.randint(88, 99)),
        ('perro', 85, random.randint(88, 99)),
        ('gato',  60, random.randint(85, 98)),
        ('alerta', 0, random.randint(90, 99)),
        ('perro', 85, random.randint(88, 99)),
        ('gato',  60, random.randint(85, 98)),
        ('perro', 85, random.randint(88, 99)),
        ('gato',  60, random.randint(85, 98)),
    ]
    for i, (sp, gr, conf) in enumerate(detecciones, 1):
        log(B, f'#{i}', 'Enviando detección...')
        foto = elegir_foto_por_especie(sp)
        enviar_deteccion(sp, gr, conf, foto_path=foto)
        time.sleep(0.8)

    print()
    log(G, '🎉', f'Listo. Abre {SERVER}/dashboard/')
    print()


# ══════════════════════════════════════════════════════════════
#  MODO 2 — Continuo con alertas automáticas
# ══════════════════════════════════════════════════════════════

def simulacion_continua():
    print(f'\n{B}{"═"*55}')
    print(f'   MODO CONTINUO + ALERTAS AUTOMÁTICAS')
    print(f'   Ctrl+C para detener')
    print(f'{"═"*55}{RE}\n')

    _info_fotos()
    print()

    bat, dog, cat, water = 85, 80, 75, 95
    ciclo = 0
    sent_bat = sent_dog = sent_cat = sent_water = False

    try:
        while True:
            ciclo += 1
            log(B, '🔄', f'Ciclo #{ciclo}')
            enviar_status(bat, dog, cat, water)

            if random.random() > 0.3:
                sp  = random.choice(['perro', 'perro', 'gato', 'alerta'])
                gr  = 85 if sp == 'perro' else 60 if sp == 'gato' else 0
                foto = elegir_foto_por_especie(sp)
                enviar_deteccion(sp, gr, random.randint(85, 99), foto_path=foto)

            # ── Alertas automáticas ───────────────────────────────
            if bat <= 15 and not sent_bat:
                enviar_alerta('danger', f'{FEEDER_ID} — Batería crítica',
                    f'Batería al {bat}%. Requiere recarga inmediata o el feeder quedará fuera de línea.')
                sent_bat = True
            elif bat > 25: sent_bat = False

            if dog <= 20 and not sent_dog:
                enviar_alerta('warn', f'{FEEDER_ID} — Comida para perros baja',
                    f'Comida para perros al {dog}%. Considera rellenar pronto.')
                sent_dog = True
            elif dog > 30: sent_dog = False

            if cat <= 20 and not sent_cat:
                enviar_alerta('warn', f'{FEEDER_ID} — Comida para gatos baja',
                    f'Comida para gatos al {cat}%. Considera rellenar pronto.')
                sent_cat = True
            elif cat > 30: sent_cat = False

            if water <= 15 and not sent_water:
                enviar_alerta('danger', f'{FEEDER_ID} — Agua casi agotada',
                    f'Nivel de agua al {water}%. Rellena el depósito cuanto antes.')
                sent_water = True
            elif water > 25: sent_water = False

            # Consumo gradual
            bat   = max(5, bat   - random.randint(0, 2))
            dog   = max(5, dog   - random.randint(1, 4))
            cat   = max(5, cat   - random.randint(1, 3))
            water = max(5, water - random.randint(0, 2))

            print()
            log(W, '⏱ ', 'Esperando 10 segundos...\n')
            time.sleep(10)

    except KeyboardInterrupt:
        log(Y, '👋', 'Simulación detenida.')


# ══════════════════════════════════════════════════════════════
#  MODO 3 — Alertas manuales
# ══════════════════════════════════════════════════════════════

def menu_alertas_manuales():
    PREDEFINIDAS = [
        ('danger', f'{FEEDER_ID} — Batería crítica',
                   'Batería al 8%. Requiere recarga inmediata.'),
        ('warn',   f'{FEEDER_ID} — Comida para perros baja',
                   'Comida para perros al 14%. Considera rellenar.'),
        ('warn',   f'{FEEDER_ID} — Comida para gatos baja',
                   'Comida para gatos al 11%. Considera rellenar.'),
        ('danger', f'{FEEDER_ID} — Agua casi agotada',
                   'Nivel de agua al 6%. Rellena el depósito.'),
        ('danger', f'{FEEDER_ID} — Humano detectado',
                   'La cámara detectó una persona cerca del feeder con 99% de confianza.'),
        ('warn',   f'{FEEDER_ID} — Sin conexión WiFi',
                   'El feeder perdió conexión por más de 5 minutos.'),
        ('warn',   f'{FEEDER_ID} — Temperatura alta',
                   'Temperatura interna del feeder supera los 45°C.'),
        ('ok',     f'{FEEDER_ID} — Feeder rellenado',
                   'Niveles restaurados. Comida y agua al 100%.'),
        ('ok',     f'{FEEDER_ID} — Reconectado',
                   'El feeder recuperó la conexión exitosamente.'),
    ]

    print(f'\n{M}{"═"*55}')
    print(f'   ENVÍO MANUAL DE ALERTAS / NOTIFICACIONES')
    print(f'{"═"*55}{RE}\n')

    COLOR = {'danger': R, 'warn': Y, 'ok': G}
    print(f'{W}Alertas predefinidas:{RE}')
    for i, (tipo, titulo, _) in enumerate(PREDEFINIDAS, 1):
        c = COLOR[tipo]
        print(f'  {c}{i:2}{RE} [{tipo.upper():6}] {titulo}')

    print(f'\n  {W} 0{RE} — Enviar TODAS de golpe')
    print(f'  {W}99{RE} — Escribir alerta personalizada\n')

    opcion = input('Elige opción: ').strip()

    if opcion == '0':
        log(Y, '📤', f'Enviando {len(PREDEFINIDAS)} alertas...')
        for tipo, titulo, desc in PREDEFINIDAS:
            enviar_alerta(tipo, titulo, desc)
            time.sleep(0.35)
        print()
        log(G, '✅', 'Todas enviadas. Revisa el panel de Alertas (sync cada ~15s).')

    elif opcion == '99':
        print(f'\n{W}Tipo:{RE}  {R}1{RE} danger   {Y}2{RE} warn   {G}3{RE} ok')
        t      = input('Tipo (1/2/3): ').strip()
        tipo   = {'1': 'danger', '2': 'warn', '3': 'ok'}.get(t, 'warn')
        titulo = input('Título: ').strip()
        desc   = input('Descripción: ').strip()
        if titulo:
            enviar_alerta(tipo, titulo, desc)
            log(G, '✅', 'Alerta enviada.')
        else:
            log(R, '❌', 'El título no puede estar vacío.')

    elif opcion.isdigit() and 1 <= int(opcion) <= len(PREDEFINIDAS):
        tipo, titulo, desc = PREDEFINIDAS[int(opcion) - 1]
        enviar_alerta(tipo, titulo, desc)
        print()
        log(G, '✅', 'Alerta enviada. Aparece en el panel en el próximo sync (~15s).')

    else:
        log(R, '❌', 'Opción no válida.')


# ══════════════════════════════════════════════════════════════
#  MODO 5 — Envío manual de detección con foto
# ══════════════════════════════════════════════════════════════

def menu_deteccion_con_foto():
    print(f'\n{B}{"═"*55}')
    print(f'   ENVÍO MANUAL DE DETECCIÓN + FOTO')
    print(f'{"═"*55}{RE}\n')

    _info_fotos()
    fotos = listar_fotos()

    # Especie
    print(f'\n{W}Especie:{RE}  {G}1{RE} perro   {B}2{RE} gato   {Y}3{RE} alerta')
    sp_opt = input('Elige especie (1/2/3): ').strip()
    sp     = {'1': 'perro', '2': 'gato', '3': 'alerta'}.get(sp_opt, 'perro')
    gr     = 85 if sp == 'perro' else 60 if sp == 'gato' else 0
    conf   = random.randint(88, 99)

    # Foto
    foto_path = None
    if fotos:
        print(f'\n{W}Opciones de foto:{RE}')
        print(f'  {G}1{RE} — Elegir automáticamente por especie')
        print(f'  {B}2{RE} — Elegir aleatoriamente de la carpeta')
        print(f'  {Y}3{RE} — Seleccionar manualmente de la lista')
        print(f'  {R}4{RE} — Sin foto')
        foto_opt = input('Opción foto (1/2/3/4): ').strip()

        if foto_opt == '1':
            foto_path = elegir_foto_por_especie(sp)
        elif foto_opt == '2':
            foto_path = elegir_foto_aleatoria()
        elif foto_opt == '3':
            print(f'\n{W}Fotos disponibles:{RE}')
            for i, f in enumerate(fotos, 1):
                size_kb = f.stat().st_size // 1024
                print(f'  {G}{i:2}{RE} {f.name}  ({size_kb} KB)')
            idx = input('\nNúmero de foto: ').strip()
            if idx.isdigit() and 1 <= int(idx) <= len(fotos):
                foto_path = fotos[int(idx) - 1]
            else:
                log(Y, '⚠️', 'Número no válido, se enviará sin foto.')
        # opcion 4 o cualquier otra: foto_path queda None
    else:
        log(Y, '📂', 'No hay fotos en la carpeta, se enviará sin foto.')

    print()
    enviar_deteccion(sp, gr, conf, foto_path=foto_path)
    print()
    log(G, '✅', 'Detección enviada.')


# ══════════════════════════════════════════════════════════════
#  MENÚ PRINCIPAL
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print(f'\n{W}╔══════════════════════════════════════════════╗')
    print(f'║   SIMULADOR ESP32 — EcoSentinel Feeder       ║')
    print(f'║   Servidor : {SERVER:<30} ║')
    print(f'║   Feeder   : {FEEDER_ID:<30} ║')
    print(f'║   Fotos    : {PHOTOS_DIR:<30} ║')
    print(f'╚══════════════════════════════════════════════╝{RE}\n')

    # Mostrar cuántas fotos hay al arrancar
    _info_fotos()
    print()

    print(f'  {G}1{RE} — Simulación completa  (status + detecciones con fotos, termina solo)')
    print(f'  {B}2{RE} — Modo continuo        (tiempo real + alertas automáticas)')
    print(f'  {M}3{RE} — Alertas manuales     (elige qué notificación enviar)')
    print(f'  {Y}4{RE} — Verificar endpoints  (ping a dashboard e historial)')
    print(f'  {G}5{RE} — Detección manual     (elige especie + foto manualmente)\n')

    op = input('Elige una opción (1/2/3/4/5): ').strip()

    if   op == '1': simulacion_completa()
    elif op == '2': simulacion_continua()
    elif op == '3': menu_alertas_manuales()
    elif op == '4':
        print(); verificar_endpoints(); print()
    elif op == '5': menu_deteccion_con_foto()
    else:
        print(f'{R}Opción no válida.{RE}')