from typing import Any
from django import forms
from .models import Country
import pycountry


class CountryForm(forms.ModelForm):
    countries = [('', 'Select a country')] + [(country.alpha_2, country.name) for country in pycountry.countries]
    country = forms.ChoiceField(choices=countries, validators=[lambda x: x != ''])

    class Meta:
        model = Country
        exclude = ['name', 'code']

    def clean(self):
        cleaned_data = super().clean()
        country_code = cleaned_data.get('country')
        if country_code:
            for code, name in [[c.alpha_2, c.name] for c in list(pycountry.countries)]:
                if code == country_code:
                    cleaned_data['name'] = name
                    cleaned_data['code'] = code
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.code = self.cleaned_data['code']
        instance.name = self.cleaned_data['name']
        if commit:
            instance.save()
        return instance
