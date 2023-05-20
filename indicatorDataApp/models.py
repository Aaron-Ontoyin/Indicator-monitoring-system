from django.db import models
from django.db.models import Sum, Min, Max, Q
from statistics import mean, median
from abc import ABC, abstractmethod
import pycountry

from dateutil.rrule import rrule, YEARLY
from datetime import datetime



# Choice Fiels
class MeasurementUnitChoice(models.TextChoices):
    """The unit of measurement for an indicator"""
    PERCENTAGE = 'Per', 'Percentage'
    NUMBER = 'Num', 'Number'


class MeasurementFreqChoice(models.TextChoices):
    """The frequency of measurement for an indicator"""
    BIENNIAL = 'Bien', 'Biennial [2]'
    YEARLY = 'Yr', 'Yearly [1]'
    BIANNUALLY = 'Bia', 'Biannually [1/2]'
    QUARTERLY = 'Qr', 'Quarterly [1/4]'
    MONTHLY = 'Mt', 'Monthly [1/12]'
    WEEKLY = 'Wk', 'Weekly [1/52]'
    DAILY = 'Dy', 'Daily [1/365.5]'


class AggregationLevelChoice(models.TextChoices):
    """The aggregation level for an indicator"""
    DISTRICT = 'Dis', 'District'
    REGIONAL = 'Reg', 'Regional'
    NATIONAL = 'Nat', 'National'        


class MeasurementLevelChoice(models.TextChoices):
    """Choices for level of measurement"""
    INPUT = 'Inp', 'Input'
    OUTPUT = 'Outp', 'Output'
    OUTCOME = 'Outc', 'Outcome'
    INPACT = 'Inpc', 'Inpact'


class ValueTypeChoice(models.TextChoices):
    """Choices for value type"""
    COMPUTED = 'C', 'Computed'
    INPUTTED = 'I', 'Inputted'


class CalFormatChoice(models.TextChoices):
    """Choices for cal format"""
    AVERAGE = 'Ave', 'Average'
    NET = 'Net', 'Net'
    MEAN = 'Mean', 'Mean'
    MEDIAN = 'Mdn', 'Median'


#Models
class Country(models.Model):
    """A normal country"""

    name = models.CharField(max_length=60, unique=True)
    code = models.CharField(max_length=2, unique=True)

    class Meta:
        verbose_name_plural = 'Countries'

    def __str__(self) -> str:
        return self.name + " (" + self.code + ")"


class Region(models.Model):
    """Region of a country"""

    name = models.CharField(max_length=60)
    code = models.CharField(max_length=10, unique=True)
    country = models.ForeignKey(Country, related_name='regions', on_delete=models.CASCADE)

    def __str__(self):
        return self.name + " " + self.country.code


class District(models.Model):
    """Destrict of a Region"""

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10, unique=True)
    region = models.ForeignKey(Region, related_name='districts', on_delete=models.CASCADE)


class Value(models.Model):
    """The actual value a Variable"""
    period = models.DateField(auto_now_add=True)
    inputted_value = models.DecimalField(decimal_places=2, max_digits=9, default=None)

    computing_funcs = {
        CalFormatChoice.AVERAGE: lambda x: sum(x) / len(x),
        CalFormatChoice.NET: sum,
        CalFormatChoice.MEAN: mean,
        CalFormatChoice.MEDIAN: median,
    }

    # Not explicitely made abstract but they are abstract
    value_type = None    
    def computed_value(self):
        pass
    
    def compute(self, values, compute_format):
        """Computes values base on compute format"""
        computing_func = self.computing_funcs.get(compute_format)
        return computing_func(values)

    @property
    def value(self):
        if self.value_type == ValueTypeChoice.INPUTTED:
            return self.inputted_value
        return self.computed_value()


class NationalVarValue(Value):
    """The value at a period for a national variable"""
    variable = models.ForeignKey('NationalIndicatorVariable',
                                 related_name='value_models',
                                 on_delete=models.CASCADE)
    @property
    def value_type(self):
        return self.variable.indicator_var.value_type

    def computed_value(self):
        #TODO: Values should be computed and stored once and for all
        """Returns the computed value instead of inputted value"""
        regional_vars = RegionalIndicatorVariable.objects.filter(
            Q(region__country=self.variable.country) &
            Q(country_var__indicator_var=self.variable.indicator_var)
        )
        regional_var_values = RegionalVarValue.objects.filter(variable__in=regional_vars)
        all_values = regional_var_values.values_list('value_value', flat=True)
        
        return self.compute(all_values, self.variable.indicator_var.compute_format)


class RegionalVarValue(Value):
    """The value at a period for a regional variable"""
    variable = models.ForeignKey('RegionalIndicatorVariable',
                                 related_name='value_models',
                                 on_delete=models.CASCADE)
    @property
    def value_type(self):
        return self.variable.national_var.indicator_var.value_type
    
    def computed_value(self):
        """Returns the computed value instead of inputted value"""
        indicator_variable = self.variable.national_var.indicator_var
        district_vars = DistrictIndicatorVariable.objects.filter(
            Q(district__region=self.variable.region) &
            Q(regional_var__national_var__indicator_var=indicator_variable)
        )
        district_var_values = DistrictVarValue.objects.filter(variable__in=district_vars)
        all_values = district_var_values.value_list('value__value', flat=True) 
        
        return self.compute(all_values, self.variable.national_var.indicator_var.compute_format)


class DistrictVarValue(Value):
    """The value at a period for a district variable"""
    variable = models.ForeignKey('DistrictIndicatorVariable',
                                 related_name='value_models',
                                 on_delete=models.CASCADE)
    
    def computed_value(self):
        """Region has no computed values, so returns inputted value"""
        return self.inputted_value

    @property
    def value_type(self):
        return self.variable.regional_var.national_var.indicator_var.value_type


class IndicatorVariable(models.Model):
    """Base Indicator variable"""

    name = models.CharField(max_length=250)
    code = models.CharField(max_length=5)
    country = models.ForeignKey(Country, related_name='variables', on_delete=models.CASCADE) 
    value_type = models.CharField(max_length=10, choices=ValueTypeChoice.choices)
    level = models.CharField(max_length=10,
                             choices=AggregationLevelChoice.choices,
                             default=AggregationLevelChoice.NATIONAL)
    compute_format = models.CharField(max_length=10,
                                        choices=CalFormatChoice.choices,
                                        default=CalFormatChoice.NET)

    def get_all_district_vars(self):
        district_vars = DistrictIndicatorVariable.objects.filter(
            regional_var__national_var__indicator_var=self
        )
        return district_vars

    def get_all_regional_vars(self):
        reg_vars = RegionalIndicatorVariable.objects.filter(national_var__indicator_var=self)
        return reg_vars
    
    def get_regional_var(self, target=None):
        """
        Returns the var of a region or set of all vars for regions in a country
        Input:
            target - if region, returns total value for the region, else if
            country or None, returns all regional_vars for the country
        """
        if target is None or target.isinstance(Country):
            return self.get_all_regional_vars()
        elif target.isinstance(Region):
            return self.get_all_regional_vars().get(region=target)
        else:
            raise ValueError("Target must be a Region or Country or None")

    def get_district_var(self, target):
        """
        Returns the district var(s) in a region
        Input:
            target -> target district
        """
        if target.isinstance(Region):
            # Get all district vars in target region
            return self.get_all_district_vars().filter(district__region=target)
        
        if target.isinstance(District):
            return self.get_all_district_vars().get(district=target)
        
        raise ValueError("Target must be a Region or District")

    def get_create_national_var(self):
        NationalIndicatorVariable.objects.get_or_create(
            indicator_var=self,
            defaults={'name': self.country.code + ' ' + self.name}
        )

    def delete_national_var(self):
        self.national_var.delete()

    def get_create_regional_vars(self):
        self.national_var.get_create_regional_vars()

    def delete_regional_vars(self):
        self.national_var.delete_regional_vars()

    def create_district_vars(self):
        for var in self.national_var.regional_vars.all():
            var.create_district_vars()

    def delete_district_vars(self):
        for var in self.national_var.regional_vars.all():
            var.delete_district_vars()
            

    def get(self, target=None, get_net_value=True, get_all_districts=False):
        """
        Get the var of a country, region or district indicator variable(s).
        Call without any input to get the national var
        Call with get_net_value == False to get all regional vars of the var
        Call with get_all_districts == True to get all district vars of the var
        Input
            target -> the target region or district of the indicator variable,
                    leave blank for this country as target.
            get_net_value -> determines if should return the total indicator value
                    for the country or set of all regional values in the country
                    likewise region on districts
            get_all_districts -> If true, returns all district vars regardless of nothing
        """

        if get_all_districts:
            return self.get_all_district_vars()
        
        if target.isinstance(Country) or target is None:
            if get_net_value:
                return self.national_var
            return self.get_all_regional_vars()
        
        if target.isinstance(Region):
            if get_net_value:
                return self.get_regional_var(target)
            else:
                # Get all district vars in target region
                return self.get_district_var(target)
        
        if target.isinstance(District):
            return self.get_district_var(target)
        
        raise ValueError("Target must be a Region, Country, District or None")
        
    def __str__(self):
        return self.country.code + " " + self.name + " | " + self.code


class NationalIndicatorVariable(models.Model):
    """
    National level indicator variable.
    Automatically creates Regional level indicators
    if level is deeper than national
    """

    name = models.CharField(max_length=150)
    indicator_var = models.OneToOneField(IndicatorVariable,
                                      related_name='national_var',
                                      on_delete=models.CASCADE)
    # Linked to value_models on a ForeignKey
    
    @property
    def values(self):
        return self.value_models.all()
    
    def get_create_regional_vars(self):
        for region in self.indicator_var.country.regions.all():
            RegionalIndicatorVariable.objects.get_or_create(
                national_var = self,
                region=region,
                name = self.name + ' ' + region.code
            )
    
    def delete_regional_vars(self):
        RegionalIndicatorVariable.objects.filter(national_var=self).delete()

    def get_value_at(self, date):
        all_vars_at_date = self.value_models.filter(pariod__gte=date)
        least_var = all_vars_at_date.order_by('period').first()
        return least_var.value

    def __str__(self):
        return self.name


class RegionalIndicatorVariable(models.Model):
    """
    Regional level indicator variable.
    Automatically creates District level indicators
    if level is deeper than regional
    """

    name = models.CharField(max_length=150)
    region = models.ForeignKey(Region, related_name='variables', on_delete=models.CASCADE)
    national_var = models.ForeignKey(NationalIndicatorVariable,
                                    related_name='regional_vars',
                                    on_delete=models.CASCADE)
    # Linked to value_models by ForeignKey
    
    @property
    def values(self):
        return self.value_models.all()

    def get_value_at(self, date):
        all_vars_at_date = self.value_models.filter(pariod__gte=date)
        least_var = all_vars_at_date.order_by('period').first()
        return least_var.value

    def get_create_district_vars(self):
        districts = District.objects.filter(
            region__country=self.national_var.indicator_var.country
        )
        for district in districts:
            regional_var = RegionalIndicatorVariable.objects.get(
                Q(region=district.region) & Q(national_var=self.national_var)
            )
            DistrictIndicatorVariable.objects.get_or_create(
                regional_var = regional_var,
                district = district,
                name = self.name + '_' + self.name,
            )
    
    def delete_district_vars(self):
        DistrictIndicatorVariable.objects.filter(regional_var=self).delete()

    def __str__(self):
        return self.name


class DistrictIndicatorVariable(models.Model):
    """District level indicator variable"""

    name = models.CharField(max_length=150)
    regional_var = models.ForeignKey(RegionalIndicatorVariable,
                                     related_name='district_vars',
                                     on_delete=models.CASCADE)

    def get_value_at(self, date):
        all_vars_at_date = self.value_models.filter(pariod__gte=date)
        least_var = all_vars_at_date.order_by('period').first()
        return least_var.value

    @property
    def values(self):
        return self.value_models.all()


class IndicatorValue(models.Model):
    """The actual value of an indicator at a particular period"""
    period = models.DateField()
    indicator = models.ForeignKey('Indicator', related_name='values', on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)

    # @staticmethod
    # def create(indicator):
    #     """Creates a new indicator value for the current period"""
    #     IndicatorValue.objects.create(
    #         indicator=indicator
    #     )


class Indicator(models.Model):
    """The base Item in this project is the indicator"""
    
    name = models.CharField(max_length=250)
    code = models.CharField(max_length=150)
    definition = models.TextField(null=True, blank=True)
    country = models.ForeignKey(Country, related_name='indicators', on_delete=models.CASCADE)
    responsible_party = models.CharField(max_length=500, null=True, blank=True)
    measurement_unit = models.CharField(max_length=10, choices=MeasurementUnitChoice.choices)
    measurement_freq = models.CharField(max_length=10, choices=MeasurementFreqChoice.choices, null=True)
    measurement_level = models.CharField(max_length=10, choices=MeasurementLevelChoice.choices, null=True)
    data_source = models.TextField(null=True, blank=True)
    level = models.CharField(max_length=10, choices=AggregationLevelChoice.choices, null=True)
    variables = models.ManyToManyField(IndicatorVariable,
                                       related_name='indicators',
                                       blank=True)
    computing_formula = models.CharField(max_length=250, blank=True, null=True,
                                         help_text="Not useful if only one variable is selected.\
                                            Leave blank to use addtion of all varibles.")

    def value_at(self, date):
        """
        Returns the value of this indicator at the given date
        If indicator is not national, returns the value at each division for this date
        """
        vars_dict = self.get_vars_dict()
        computed_vals = []

        sorted_vars_dict = {} # place and it's variables
        for k, v in vars_dict.items():
            if v not in sorted_vars_dict:
                sorted_vars_dict[v] = {k: v}
            else:
                sorted_vars_dict[v][k] = v
        
        for place, places_vars in sorted_vars_dict:
            value = eval(self.computing_formula.replace('^', '**'),
                            {code: var.get_value_at(date) for code, var in places_vars})
            computed_vals.append({place: value})

        return computed_vals
        

    def get_vars_dict(self):
        """Returns a dict of indicator variables and their codes according to self.level"""
        if self.level == AggregationLevelChoice.NATIONAL:
            vars_dict = {
                v.code: v.get(target=self.country, get_net_value=True)
                for v in self.variables
            }
        
        if self.level == AggregationLevelChoice.REGIONAL:
            vars_dict = {
                v.code: v.get(target=self.country, get_net_value=False)
                for v in self.variables
            }

        if self.level == AggregationLevelChoice.DISTRICT:
            vars_dict = {
                v.code: v.get(all_district_vars=True)
                for v in self.variables
            }

        return vars_dict

    @property
    def all_vars_values(self):
        all_values = []
        for var in self.get_vars_dict.values():
            for value in var.value_models.all():
                all_values.append(value)
        return all_values

    def get_min_date(self):
        min_date_per_value = []
        for var in self.all_vars_values:
            min_date_per_value.append((var.value_models.all().aggregate(Min('period')))['period__min'])

        return min(min_date_per_value)

    def get_max_date(self):
        max_date_per_value = []
        for var in self.all_vars_values:
            max_date_per_value.append((var.value_models.all().aggregate(Max('period')))['period__max'])
        
        return max(max_date_per_value)

    def divide_dates(self):
        freg_string = self.get_measurement_freq_label.split('[')[1][:-1]
        record_per_yr = eval(freg_string)

        intervals = list(
            rrule(YEARLY, 
                  interval=record_per_yr,
                  dtstart=self.get_min_date(),
                  until=self.get_max_date()
                  )
        )
        return intervals

    def data(self):
        """Returns indicator values in pd dataframe format"""
        import pandas as pd

        dates = self.divide_dates()
        values = {date: self.value_at(date) for date in dates}

        return pd.DataFrame(values)
    
    def __str__(self):
        return self.name + ' ' + self.country.code 
