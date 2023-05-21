from django.shortcuts import render
from django.views.generic import View
from datetime import datetime
from django.contrib import messages

from .models import NationalIndicatorVariable, RegionalIndicatorVariable, DistrictIndicatorVariable, NationalVarValue, RegionalVarValue, DistrictVarValue


class InputDataView(View):
    """
    View for letting users access indicator variables they are 
    permitted to edit
    """
    from itertools import chain
    queryset = chain(NationalIndicatorVariable.objects.all(),
                 RegionalIndicatorVariable.objects.all(),
                 DistrictIndicatorVariable.objects.all())

    def get(self, request,*args, **kwargs):
        var_pk = kwargs.get('var_pk')
        var_class = kwargs.get('var_class_name')

        existing_value_pk = kwargs.get('existing_value_pk')

        # If a variable was clicked on, get it or set variable to ""
        variable = ""
        if var_pk and var_class:
            variable = globals().get(var_class).objects.get(pk=var_pk)

        # If an existing value was clicked on, get it or set existing value to ""
        existing_value = ""        
        if existing_value_pk:
            existing_value = variable.value_models.get(pk=existing_value_pk)
            variable = existing_value.variable

        queryset = RegionalIndicatorVariable.objects.all()

        context = {'variables': queryset, 'variable': variable, 'existing_value': existing_value}
        return render(request, 'indicatorDataApp/input_data.html', context)

    def post(self, request, *args, **kwargs):
        value = request.POST.get("var_value")
        date = request.POST.get("var_value_date")
        variable_pk = request.POST.get("variable_pk")
        variable_class = request.POST.get("variable_class")
        
        existing_value_pk = request.POST.get("existing_value_pk")
        existing_value = None

        if variable_class == "NationalIndicatorVariable":
            if existing_value_pk:
                existing_value  = NationalVarValue.objects.get(pk=existing_value_pk)

            variable = NationalIndicatorVariable.objects.get(pk=variable_pk)

        if variable_class == "RegionalIndicatorVariable":
            if existing_value_pk:
                existing_value  = RegionalVarValue.objects.get(pk=existing_value_pk)

            variable = RegionalIndicatorVariable.objects.get(pk=variable_pk)

        if variable_class == "DistrictIndicatorVariable":
            if existing_value_pk:
                existing_value  = DistrictVarValue.objects.get(pk=existing_value_pk)

            variable = DistrictIndicatorVariable.objects.get(pk=variable_pk)

        if value and date:
            if existing_value:
                existing_value.period = datetime.strptime(date, "%Y-%m-%d")
                existing_value.inputted_value = float(value)
                existing_value.save()
                messages.success(request, f"Value for {date} update to {float(value)} successfully")
            else:
                variable.create_value(
                    period=datetime.strptime(date, "%Y-%m-%d"),
                    inputted_value=float(value)
                )
                messages.success(request, "Value added successfully")

        elif date:
            messages.error(request, "Invalide value!")
            print("Invalide value!")
        else:
            messages.error(request, "Invalide Date!")
            print("Invalide date!")

        return self.get(request, *args, **kwargs)