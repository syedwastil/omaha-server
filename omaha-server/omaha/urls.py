
from django.urls import path
from django.conf.urls import include
from omaha import views

urlpatterns = [
    path('service/update2/', views.UpdateView.as_view(), name='update'),
]

