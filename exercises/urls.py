from django.urls import path, include
from .views import ArticlesView

urlpatterns = [
    path ('articles/', ArticlesView.as_view(), name='articles_list')
]
