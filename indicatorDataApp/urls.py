from django.urls import path
from django.contrib.auth.views import LoginView
from .views import InputDataView

urlpatterns = [
    path('', LoginView.as_view(template_name='login.html'), name='login'),
    path('input-data/', InputDataView.as_view(template_name='indicatorDataApp/input_data.html'), name='input_data'),
]
