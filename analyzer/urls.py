from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_page, name='upload_page'),
    path('analyze/', views.analyze_page, name='analyze_page'),
    path('api/upload/', views.upload_code, name='upload_code'),
    path('api/analyze/', views.analyze_code, name='analyze_code'),
]
