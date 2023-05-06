from django.contrib import admin
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import Country, Region, District
from .models import Indicator, IndicatorVariable, NationalIndicatorVariable
from .models import  RegionalIndicatorVariable, DistrictIndicatorVariable
from .models import Value, AggregationLevelChoice
from .models import NationalVarValue, RegionalVarValue, DistrictVarValue
from .forms import CountryForm



class CountryAdmin(admin.ModelAdmin):
    form  = CountryForm


class IndicatorAdminForm(forms.ModelForm):
    class Meta:
        model = Indicator
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.country_id:
            self.fields['variables'].queryset = IndicatorVariable.objects.filter(country_id=self.instance.country_id)
        else:
            self.fields['variables'].queryset = IndicatorVariable.objects.none() # Div would be deleted anyway

    def clean(self):
        cleaned_data = super().clean()
        variables = cleaned_data.get('variables')
        
        if variables:
            level = self.cleaned_data.get('level')
            error_msgs = []
            for variable in variables.all():
                print(level, variable.level)
                if ((variable.level == AggregationLevelChoice.NATIONAL) or\
                    (variable.level == AggregationLevelChoice.REGIONAL)) and\
                    (level == AggregationLevelChoice.DISTRICT):
                    error_msgs.append(f'{variable} is a {variable.get_level_display()} level variable')
                
                if (variable.level == AggregationLevelChoice.NATIONAL) and\
                    (level == AggregationLevelChoice.REGIONAL):
                    error_msgs.append(f'{variable} is a {variable.get_level_display()} level variable')

            if error_msgs:
                raise ValidationError(error_msgs)

        return cleaned_data

class IndicatorAdmin(admin.ModelAdmin):
    form = IndicatorAdminForm

    filter_horizontal = ('variables',)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['creating'] = True
        return super().add_view(request, form_url=form_url, extra_context=extra_context)


class IndicatorVariableAdmin(admin.ModelAdmin):
    #TODO: make sure districts for country exist if level chosen district
    pass



admin.site.register(Value)
admin.site.register(Country, CountryAdmin)
admin.site.register(District)
admin.site.register(Region)
admin.site.register(Indicator, IndicatorAdmin)
admin.site.register(IndicatorVariable, IndicatorVariableAdmin)
admin.site.register(NationalIndicatorVariable)
admin.site.register(RegionalIndicatorVariable)
admin.site.register(DistrictIndicatorVariable)
admin.site.register(NationalVarValue)
admin.site.register(RegionalVarValue)
admin.site.register(DistrictVarValue)