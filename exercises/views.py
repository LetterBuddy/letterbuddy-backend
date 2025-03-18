from django.shortcuts import render
from .models import *
from accounts.permissions import IsAuthenticatedAdult
from rest_framework import generics, status
from .serializers import *

class ArticlesView(generics.ListAPIView):
    serializer_class = ArticleSerializer
    permission_classes = (IsAuthenticatedAdult, )
    queryset = Article.objects.all()

    





