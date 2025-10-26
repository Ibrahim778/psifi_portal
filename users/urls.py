"""
URL configuration for psifi_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('', views.home_view, name='home'),
    # path('admin/', admin.site.urls), Not needed. Already present in psifi_portal/urls.py
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('team_detail/<int:pk>/', views.team_detail_view, name='team_detail'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('register/', views.register_page, name='register_page'),
    path("tally/webhook/", views.tally_webhook, name="tally_webhook"),
    path('payment_voucher/', views.payment_voucher_view, name='payment_voucher'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('contact/', views.contact, name='contact'),
    path('categories/', views.categories, name='categories'),
    path('aiml/', views.aiml, name='aiml'),
    path('quantum/', views.quantum, name='quantum'),
    path('life/', views.life, name='life'),
    path('auto/', views.auto, name='auto'),
    path('media/', views.media, name='media'),
    path('cad/', views.cadashboard, name='ca'),
    path('ca_login/', views.ca_login_view, name='calog'),
    path('ca_signup/', views.casignup, name='ca_signup'),
    path('name-password-reset/', views.name_password_reset,
         name='name_password_reset'),
    path('schedule/', views.schedule_view, name='schedule'),

    # Paymo endpoints
    path('api/create-payment/', views.create_payment, name='create_payment'),
    path('api/paymo/callback/', views.paymo_callback, name='paymo_callback'),
    
    # cognito form link saving
    path('api/cognitostore', views.CongitoLinkStore.as_view(), name='cognito_store'),
    path('api/cognitoget', views.CognitoLinkGet.as_view(), name='cognito_get'),

    # Sheets debug endpoint (temporary)
    path('api/debug/sheets-append/', views.debug_sheets_append, name='debug_sheets_append'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
