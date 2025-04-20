# 1. chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('api/', views.chat_api, name='chat_api'),
    path('api/select_model/', views.select_model, name='select_model'),
]

import sys
print(sys.executable)  # Pythonインタプリタのパス
print(sys.path)  # Pythonの検索パス

import os
print(os.environ.get('PYTHONPATH'))