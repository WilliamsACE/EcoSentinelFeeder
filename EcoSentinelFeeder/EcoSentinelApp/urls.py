from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('',                      views.home,         name='home'),
    path('donar/',            views.donar,         name='donar'),
    path('dashboardDocs/', views.dashboardDocs, name='dashboardDocs'),


    path('login/',              views.login_view,        name='login'),
    path('logout/',             views.logout_view,       name='logout'),
    path('api/auth/login/',     views.login_api,         name='login_api'), 

    path('dashboard/',            views.dashboard,         name='dashboard'),
    path('mapa/',               views.mapa,              name='mapa'),

    path('api/feeder/status/',    views.receive_status,    name='receive_status'),
    path('api/feeder/detection/', views.receive_detection, name='receive_detection'),
    path('api/dashboard/',        views.api_dashboard,     name='api_dashboard'),
    path('api/history/',          views.api_history,       name='api_history'),
    path('api/data/delete-all/', views.delete_all_data, name='delete_all_data'),

    path('api/feeder/alert/', views.receive_alert, name='receive_alert'),
    path('api/donaciones/', views.api_donaciones, name='api_donaciones'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)