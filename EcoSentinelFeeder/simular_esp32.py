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
"""

import requests
import random
import time
from datetime import datetime

# ── CONFIGURACIÓN ──────────────────────────────────────────────────
SERVER   = 'http://127.0.0.1:8000'   # URL de tu Django
TOKEN    = 'YeahPerdonenKamehameha'               # mismo token que en views.py
FEEDER_ID = 'ESF-001'                 # debe existir en la base de datos

# Colores para la terminal
G  = '\033[92m'   # verde
R  = '\033[91m'   # rojo
Y  = '\033[93m'   # amarillo
B  = '\033[94m'   # azul
W  = '\033[97m'   # blanco
RE = '\033[0m'    # reset
# ───────────────────────────────────────────────────────────────────


def log(color, icono, mensaje):
    hora = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{hora}] {icono}  {mensaje}{RE}")


def enviar_status(battery, food_dog, food_cat, water):
    """Simula el POST que manda el ESP32 cada 30 segundos."""
    payload = {
        'feeder_id': FEEDER_ID,
        'token':     TOKEN,
        'battery':   battery,
        'food_dog':  food_dog,
        'food_cat':  food_cat,
        'water':     water,
    }
    try:
        res = requests.post(f'{SERVER}/api/feeder/status/', json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            log(G, '📡', f'Status enviado → estado detectado: {data.get("status","?")}')
            log(W, '   ', f'🔋 {battery}%  🐕 {food_dog}%  🐈 {food_cat}%  💧 {water}%')
        elif res.status_code == 401:
            log(R, '🔒', f'Token incorrecto — revisa TOKEN en este script y en views.py')
        elif res.status_code == 404:
            log(R, '❓', f'Feeder "{FEEDER_ID}" no existe — créalo en el admin de Django')
        else:
            log(R, '❌', f'Error HTTP {res.status_code}: {res.text}')
    except requests.exceptions.ConnectionError:
        log(R, '🔌', f'No se pudo conectar a {SERVER} — ¿está corriendo Django?')
    except Exception as e:
        log(R, '💥', f'Error inesperado: {e}')


def enviar_deteccion(species, grams, confidence):
    """Simula el POST que manda el ESP32 al detectar un animal."""
    EMOJI = {'perro': '🐕', 'gato': '🐈', 'alerta': '⚠️'}
    payload = {
        'feeder_id':  FEEDER_ID,
        'token':      TOKEN,
        'species':    species,
        'grams':      grams,
        'confidence': confidence,
    }
    try:
        res = requests.post(f'{SERVER}/api/feeder/detection/', json=payload, timeout=5)
        if res.status_code == 200:
            log(G, EMOJI.get(species,'?'), f'Detección enviada → {species} · {grams}g · {confidence}% confianza')
        elif res.status_code == 401:
            log(R, '🔒', 'Token incorrecto')
        elif res.status_code == 404:
            log(R, '❓', f'Feeder "{FEEDER_ID}" no encontrado')
        else:
            log(R, '❌', f'Error HTTP {res.status_code}: {res.text}')
    except requests.exceptions.ConnectionError:
        log(R, '🔌', f'No se pudo conectar a {SERVER}')
    except Exception as e:
        log(R, '💥', f'Error inesperado: {e}')


def verificar_api_dashboard():
    """Verifica que el endpoint del dashboard responda correctamente."""
    try:
        res = requests.get(f'{SERVER}/api/dashboard/', timeout=5)
        if res.status_code == 200:
            data = res.json()
            feeders = data.get('feeders', [])
            log(G, '✅', f'GET /api/dashboard/ OK — {len(feeders)} feeder(s) encontrado(s)')
            for f in feeders:
                log(W, '   ', f'  → {f["id"]} {f["name"]} | estado: {f["status"]} | bat: {f["battery"]}%')
        else:
            log(R, '❌', f'GET /api/dashboard/ respondió {res.status_code}')
    except requests.exceptions.ConnectionError:
        log(R, '🔌', f'No se pudo conectar a {SERVER}')


def verificar_api_history():
    """Verifica que el endpoint del historial responda correctamente."""
    try:
        res = requests.get(f'{SERVER}/api/history/?limit=5', timeout=5)
        if res.status_code == 200:
            data = res.json()
            eventos = data.get('events', [])
            log(G, '✅', f'GET /api/history/ OK — {len(eventos)} evento(s) recientes')
            for e in eventos:
                log(W, '   ', f'  → [{e["time"]}] {e["feederId"]} | {e["emoji"]} {e["label"]} | {e["grams"]}g | {e["confidence"]}%')
        else:
            log(R, '❌', f'GET /api/history/ respondió {res.status_code}')
    except requests.exceptions.ConnectionError:
        log(R, '🔌', f'No se pudo conectar a {SERVER}')


def simulacion_completa():
    """
    Corre una simulación completa:
    1. Verifica que los endpoints respondan
    2. Manda 5 status con batería/comida bajando
    3. Manda 10 detecciones aleatorias de animales
    4. Verifica el historial al final
    """
    print(f'\n{B}{"═"*55}')
    print(f'   SIMULADOR ESP32 — EcoSentinel Feeder')
    print(f'   Servidor: {SERVER}')
    print(f'   Feeder:   {FEEDER_ID}')
    print(f'{"═"*55}{RE}\n')

    # ── PASO 1: Verificar conectividad ────────────────────────────
    log(Y, '🔍', 'Verificando endpoints del servidor...')
    verificar_api_dashboard()
    time.sleep(0.5)

    print()

    # ── PASO 2: Simular status bajando gradualmente ───────────────
    log(Y, '📉', 'Simulando 5 reportes de status (batería y comida bajando)...')
    battery  = 80
    food_dog = 75
    food_cat = 70
    water    = 90

    for i in range(1, 6):
        log(B, f'#{i}', f'Enviando status...')
        enviar_status(battery, food_dog, food_cat, water)

        # Simular consumo gradual
        battery  = max(0, battery  - random.randint(1, 4))
        food_dog = max(0, food_dog - random.randint(3, 8))
        food_cat = max(0, food_cat - random.randint(2, 6))
        water    = max(0, water    - random.randint(1, 3))

        time.sleep(1)

    print()

    # ── PASO 3: Simular detecciones de animales ───────────────────
    log(Y, '🐾', 'Simulando 10 detecciones de animales...')

    detecciones = [
        ('perro',  85, random.randint(88, 99)),
        ('gato',   60, random.randint(85, 98)),
        ('perro',  85, random.randint(88, 99)),
        ('perro',  85, random.randint(88, 99)),
        ('gato',   60, random.randint(85, 98)),
        ('alerta',  0, random.randint(90, 99)),  # humano detectado
        ('perro',  85, random.randint(88, 99)),
        ('gato',   60, random.randint(85, 98)),
        ('perro',  85, random.randint(88, 99)),
        ('gato',   60, random.randint(85, 98)),
    ]

    for i, (species, grams, confidence) in enumerate(detecciones, 1):
        log(B, f'#{i}', f'Enviando detección...')
        enviar_deteccion(species, grams, confidence)
        time.sleep(0.8)

    print()

    # ── PASO 4: Verificar que todo quedó guardado ─────────────────
    log(Y, '🔍', 'Verificando historial guardado...')
    verificar_api_history()

    print()
    log(G, '🎉', 'Simulación completa. Abre el dashboard y verifica los datos.')
    print(f'{B}   → http://127.0.0.1:8000/dashboard/{RE}\n')


def simulacion_continua():
    """
    Modo continuo: simula el ESP32 mandando datos indefinidamente.
    Útil para ver el dashboard actualizándose en tiempo real.
    Presiona Ctrl+C para detener.
    """
    print(f'\n{B}{"═"*55}')
    print(f'   MODO CONTINUO — simula ESP32 en tiempo real')
    print(f'   Presiona Ctrl+C para detener')
    print(f'{"═"*55}{RE}\n')

    battery  = 85
    food_dog = 80
    food_cat = 75
    water    = 95
    ciclo    = 0

    try:
        while True:
            ciclo += 1
            log(B, f'🔄', f'Ciclo #{ciclo}')

            # Mandar status cada ciclo
            enviar_status(battery, food_dog, food_cat, water)

            # Simular una detección aleatoria
            if random.random() > 0.3:  # 70% de probabilidad de detección
                species    = random.choice(['perro', 'perro', 'gato', 'alerta'])
                grams      = 85 if species == 'perro' else 60 if species == 'gato' else 0
                confidence = random.randint(85, 99)
                enviar_deteccion(species, grams, confidence)

            # Bajar niveles gradualmente
            battery  = max(5,  battery  - random.randint(0, 2))
            food_dog = max(5,  food_dog - random.randint(1, 4))
            food_cat = max(5,  food_cat - random.randint(1, 3))
            water    = max(10, water    - random.randint(0, 2))

            # Aviso cuando niveles estén bajos
            if food_dog < 20:
                log(Y, '⚠️ ', f'¡Comida perros baja! ({food_dog}%) — deberías ver alerta en el dashboard')
            if battery < 20:
                log(Y, '⚠️ ', f'¡Batería baja! ({battery}%) — deberías ver alerta en el dashboard')

            print()
            log(W, '⏱ ', f'Esperando 10 segundos...\n')
            time.sleep(10)

    except KeyboardInterrupt:
        log(Y, '👋', 'Simulación detenida.')


# ── MENÚ PRINCIPAL ─────────────────────────────────────────────────
if __name__ == '__main__':
    print(f'\n{W}¿Qué modo quieres correr?{RE}')
    print(f'  {G}1{RE} — Simulación completa (envía datos de una vez y termina)')
    print(f'  {B}2{RE} — Modo continuo (simula el ESP32 en tiempo real, Ctrl+C para parar)')
    print(f'  {Y}3{RE} — Solo verificar que los endpoints respondan\n')

    opcion = input('Elige una opción (1/2/3): ').strip()

    if opcion == '1':
        simulacion_completa()
    elif opcion == '2':
        simulacion_continua()
    elif opcion == '3':
        print()
        verificar_api_dashboard()
        time.sleep(0.3)
        verificar_api_history()
        print()
    else:
        print(f'{R}Opción no válida. Corre el script de nuevo.{RE}')
