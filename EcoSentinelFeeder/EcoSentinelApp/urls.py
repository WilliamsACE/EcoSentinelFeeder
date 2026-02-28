from django.urls import path
from . import views

urlpatterns = [
    path('',                      views.home,         name='home'),
    path('donar/',            views.donar,         name='donar'),


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
]