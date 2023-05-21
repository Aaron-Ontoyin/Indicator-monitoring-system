from django.urls import path
from django.contrib.auth.views import LoginView
from .views import InputDataView

urlpatterns = [
    path('', LoginView.as_view(template_name='login.html'), name='login'),
    path('input-data/', InputDataView.as_view(), name='input_data'),
    path('input-data/<str:var_class_name>/<str:var_pk>/', InputDataView.as_view(), name='update_variable'),
    path('input-data/<str:var_class_name>/<str:var_pk>/<str:existing_value_pk>/', InputDataView.as_view(), name='update_existing_value'),

]
