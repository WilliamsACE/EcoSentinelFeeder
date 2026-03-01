import json
from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.db.models.functions import TruncHour
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET

from .models import Feeder, FeederStatus, DetectionEvent

from collections import deque
_alertas_pendientes = deque(maxlen=50)

def dashboard(request):
    return render(request, 'dashboard.html')

def home(request):
    return render(request, 'home.html')

def donar(request):
    return render(request, 'donar.html')

def login(request):
    return render(request, 'login.html')


    

@csrf_exempt
@require_POST
def receive_status(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if data.get('token') != 'YeahPerdonenKamehameha':
        return JsonResponse({'error': 'No autorizado'}, status=401)

    try:
        feeder = Feeder.objects.get(feeder_id=data['feeder_id'])
    except Feeder.DoesNotExist:
        return JsonResponse({'error': 'Feeder no encontrado'}, status=404)

    battery  = int(data.get('battery',  0))
    food_dog = int(data.get('food_dog', 0))
    food_cat = int(data.get('food_cat', 0))
    water    = int(data.get('water',    0))

    status = 'warn' if (battery < 15 or food_dog < 10 or food_cat < 10) else 'online'

    FeederStatus.objects.create(
        feeder=feeder, status=status,
        battery=battery, food_dog=food_dog,
        food_cat=food_cat, water=water,
    )
    return JsonResponse({'ok': True, 'status': status})


@csrf_exempt
@require_POST
def receive_detection(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if data.get('token') != 'YeahPerdonenKamehameha':
        return JsonResponse({'error': 'No autorizado'}, status=401)

    try:
        feeder = Feeder.objects.get(feeder_id=data['feeder_id'])
    except Feeder.DoesNotExist:
        return JsonResponse({'error': 'Feeder no encontrado'}, status=404)

    DetectionEvent.objects.create(
        feeder=feeder,
        species=data.get('species', 'alerta'),
        grams=int(data.get('grams', 0)),
        confidence=int(data.get('confidence', 0)),
    )
    return JsonResponse({'ok': True})


def api_dashboard(request):

    alertas = list(_alertas_pendientes)
    _alertas_pendientes.clear()
    
    hoy = timezone.now().date()

    feeders_data = []

    for feeder in Feeder.objects.filter(is_active=True):
        try:
            latest = feeder.statuses.latest()
        except FeederStatus.DoesNotExist:
            latest = None

        eventos_hoy = feeder.events.filter(recorded_at__date=hoy)
        dogs_today  = eventos_hoy.filter(species='perro').count()
        cats_today  = eventos_hoy.filter(species='gato').count()

        if latest:
            delta = timezone.now() - latest.recorded_at
            mins  = int(delta.total_seconds() / 60)
            last_sync = f'hace {mins} min' if mins < 60 else f'hace {mins // 60} h'
            status    = 'offline' if mins > 5 else latest.status
        else:
            last_sync = 'nunca'
            status    = 'offline'

        feeders_data.append({
            'id':           feeder.feeder_id,
            'name':         feeder.name,
            'location':     feeder.location,
            'lat':          feeder.lat,
            'lng':          feeder.lng,
            'status':       status,
            'battery':      latest.battery  if latest else 0,
            'foodDog':      latest.food_dog if latest else 0,
            'foodCat':      latest.food_cat if latest else 0,
            'water':        latest.water    if latest else 0,
            'dogsToday':    dogs_today,
            'catsToday':    cats_today,
            'aiAccuracy':   96,
            'lastSync':     last_sync,
            'alertMessage': 'warn' if (latest and latest.status == 'warn') else '',
        })

    # Gráfica barras — últimas 12h
    hace_12h     = timezone.now() - timedelta(hours=12)
    horas_labels = [((timezone.now() - timedelta(hours=i)).strftime('%Hh')) for i in range(11, -1, -1)]

    eventos_agrupados = (
        DetectionEvent.objects
        .filter(recorded_at__gte=hace_12h)
        .annotate(hora=TruncHour('recorded_at'))
        .values('hora', 'species')
        .annotate(total=Count('id'))
        .order_by('hora')
    )
    dogs_h = [0] * 12
    cats_h = [0] * 12
    for e in eventos_agrupados:
        label = e['hora'].strftime('%Hh')
        if label in horas_labels:
            idx = horas_labels.index(label)
            if e['species'] == 'perro': dogs_h[idx] = e['total']
            if e['species'] == 'gato':  cats_h[idx] = e['total']

    # Gráfica línea — últimos 7 días
    labels_7d, dogs_7d, cats_7d = [], [], []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        evs = DetectionEvent.objects.filter(recorded_at__date=dia)
        labels_7d.append('Hoy' if i == 0 else dia.strftime('%a').capitalize())
        dogs_7d.append(evs.filter(species='perro').count())
        cats_7d.append(evs.filter(species='gato').count())

    # Donut — totales hoy
    dogs_hoy = DetectionEvent.objects.filter(recorded_at__date=hoy, species='perro').count()
    cats_hoy = DetectionEvent.objects.filter(recorded_at__date=hoy, species='gato').count()




    return JsonResponse({
        'feeders': feeders_data,
        'alerts': alertas,
        'charts': {
            'dispensa': {'labels': horas_labels, 'dogs': dogs_h,  'cats': cats_h},
            'species':  {'dogs': dogs_hoy, 'cats': cats_hoy},
            'trend':    {'labels': labels_7d, 'dogs': dogs_7d, 'cats': cats_7d},
        },
    })


def api_history(request):
    limit  = int(request.GET.get('limit', 20))
    events = DetectionEvent.objects.select_related('feeder')[:limit]

    EMOJI = {'perro':'🐕', 'gato':'🐈', 'alerta':'⚠️'}
    LABEL = {'perro':'Perro', 'gato':'Gato', 'alerta':'Humano'}

    return JsonResponse({'events': [{
        'time':       e.recorded_at.strftime('%H:%M'),
        'feederId':   e.feeder.feeder_id,
        'feederName': e.feeder.name,
        'species':    e.species,
        'label':      LABEL.get(e.species, e.species),
        'emoji':      EMOJI.get(e.species, '❓'),
        'grams':      e.grams,
        'confidence': e.confidence,
    } for e in events]})


# ── Login ─────────────────────────────────────────────────────────
def login_view(request):
    # Si ya está autenticado, mandarlo directo al dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'login.html')


@csrf_exempt
@require_POST
def login_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return JsonResponse({'error': 'Completa todos los campos'}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is not None:
        auth_login(request, user)   # ← auth_login en lugar de login
        return JsonResponse({'ok': True, 'redirect': '../dashboard/'})
    else:
        return JsonResponse({'error': 'Credenciales incorrectas'}, status=401)


def logout_view(request):
    auth_logout(request)            # ← auth_logout en lugar de logout
    return redirect('login')


# XD ── Protege el dashboard con login_required ───────────────────────
@login_required(login_url='/login/')
def dashboard(request):
    return render(request, 'dashboard.html')

# Haz lo mismo con las demás páginas que quieras proteger:
@login_required(login_url='/login/')
def mapa(request):
    return render(request, 'mapa.html')

@csrf_exempt
@require_POST
@login_required(login_url='/login/')
def delete_all_data(request):
    """POST /api/data/delete-all/ — borra todos los eventos y status"""
    DetectionEvent.objects.all().delete()
    FeederStatus.objects.all().delete()
    return JsonResponse({'ok': True, 'message': 'Todos los datos eliminados'})


@csrf_exempt
@require_POST
def receive_alert(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if data.get('token') != 'YeahPerdonenKamehameha':
        return JsonResponse({'error': 'No autorizado'}, status=401)

    try:
        feeder = Feeder.objects.get(feeder_id=data['feeder_id'])
    except Feeder.DoesNotExist:
        return JsonResponse({'error': 'Feeder no encontrado'}, status=404)

    _alertas_pendientes.append({
        'type':        data.get('type', 'warn'),
        'title':       data.get('title', ''),
        'description': data.get('description', ''),
        'time':        data.get('time', ''),
        'location':    data.get('location', feeder.name),
    })

    return JsonResponse({'ok': True})