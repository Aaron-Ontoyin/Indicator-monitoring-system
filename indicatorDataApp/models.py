from django.db import models
from django.db.models import Sum, Q
from django_countries.fields import CountryField


# Choice Fiels
class MeasurementUnitChoice(models.TextChoices):
    """The unit of measurement for an indicator"""
    
    PERCENTAGE = 'Perc', 'Percentage'
    NUMBER = 'Num', 'Number'


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


#Models
class Value(models.Model):
    """The actual value a Variable"""
    period = models.DateField(auto_now_add=True)
    inputted_value = models.DecimalField(decimal_places=2, max_digits=9, default=None)
    
    # Not explicitely made abstract but they are abstract
    value_type = None
    def computed_values(self):
        pass

    @property
    def value(self):
        if self.value_type == ValueTypeChoice.INPUTTED:
            return self.inputted_value
        return self.computed_values()


class NationalVarValue(Value):
    """The value at a period for a national variable"""
    variable = models.ForeignKey('NationalIndicatorVariable',
                                 related_name='value_models',
                                 on_delete=models.CASCADE)
    @property
    def value_type(self):
        return self.variable.indicator_var.value_type

    def computed_values(self):
        """Returns the computed value instead of inputted value"""
        regional_vars = RegionalIndicatorVariable.objects.filter(
            Q(region__country=self.variable.country) &
            Q(country_var__indicator_var=self.variable.indicator_var)
        )
        computed_value = None
        #TODO
        #compute value base on average, sum, etc
        return computed_value

class RegionalVarValue(Value):
    """The value at a period for a regional variable"""
    variable = models.ForeignKey('RegionalIndicatorVariable',
                                 related_name='value_models',
                                 on_delete=models.CASCADE)
    @property
    def value_type(self):
        return self.variable.national_var.indicator_var.value_type
    
    def computed_values(self):
        """Returns the computted value instead of inputted value"""
        indicator_variable = self.variable.national_var.indicator_var
        district_vars = DistrictIndicatorVariable.objects.filter(
            Q(district__region=self.variable.region) &
            Q(regional_var__national_var__indicator_var=indicator_variable)
        )
        computed_value = None
        #TODO
        #compute value base on average, sum, etc
        return computed_value


class DistrictVarValue(Value):
    """The value at a period for a district variable"""
    variable = models.ForeignKey('DistrictIndicatorVariable',
                                 related_name='value_models',
                                 on_delete=models.CASCADE)
    
    def computed_values(self):
        """Region has no computted values, so returns inputted value"""
        return self.inputted_value

    @property
    def value_type(self):
        return self.variable.regional_var.national_var.indicator_var.value_type


class IndicatorValue(models.Model):
    """The actual value of an indicator"""
    period = models.DateField(auto_now_add=True)
    indicator = models.ForeignKey('Indicator', related_name='values', on_delete=models.CASCADE)

    @property
    def value(self):
        pass


class Country(models.Model):
    """A normal country"""

    name = models.CharField(max_length=60)
    code = models.CharField(max_length=3)


class Region(models.Model):
    """Region of a country"""

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=3)
    country = models.ForeignKey(Country, related_name='regions', on_delete=models.CASCADE)


class District(models.Model):
    """Destrict of a Region"""

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=7)
    region = models.ForeignKey(Region, related_name='districts', on_delete=models.CASCADE)


class IndicatorVariable(models.Model):
    """Indicator variable"""

    name = models.CharField(max_length=250)
    code = models.CharField(max_length=5)
    country = models.ForeignKey(Country, related_name='variables', on_delete=models.CASCADE) 
    value_type = models.CharField(max_length=1, choices=ValueTypeChoice.choices)
    level = models.CharField(max_length=3,
                             choices=AggregationLevelChoice.choices,
                             default=AggregationLevelChoice.NATIONAL)

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

    def get(self, target=None, get_net_value=True, get_all_districts=False):
        """
        Get the value of a country, region or district indicator variable(s).
        Call without any input to get the total national value
        Call with get_net_value == False to get all regional values of the var
        Call with get_all_districts == True to get all district values of the var
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
    
    def create_vars(self):
        """
        Create indicator variables for a country, region and/or district
        Eg. if level is Nat and country is Ghana, creates the var for all
        regions in Ghana and Ghana
        Input:
            level -> 'c' for country, 'r' for regional and 'd' for district
            country -> country to create vars for
        """
        if not self.national_var:
            NationalIndicatorVariable.objects.create(
                name = self.name + '_' + self.country.code,
                indicator_var = self,
            )

        if (self.level is AggregationLevelChoice.REGIONAL or\
            self.level is AggregationLevelChoice.DISTRICT):

            for region in self.country.regions.all():
                if not self.get_regional_var(region=region):
                    RegionalIndicatorVariable.objects.create(
                        name = self.name + '_' + self.country.code + '_' + region.code,
                        national_var = self.national_var,
                    )
        
        if self.level is AggregationLevelChoice.DISTRICT:
            for district in District.objects.filter(region__country=self.country):
                if not self.get_district_var(district=district):
                    regional_var = RegionalIndicatorVariable.objects.get(
                        Q(region=district.region) & Q(national_var=self.national_var)
                    )
                    DistrictIndicatorVariable.objects.create(
                        name = self.name + '_' + self.country.code + '_' + 
                                district.region.code + '_' + district.code,
                        regional_var = regional_var,
                    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.create_vars()
        

class NationalIndicatorVariable(models.Model):
    """
    National level indicator variable.
    Automatically creates Regional level indicators
    if level is deeper than national
    """

    name = models.CharField(max_length=150)
    indicator_var = models.ForeignKey(IndicatorVariable,
                                      related_name='national_var',
                                      on_delete=models.CASCADE)
    # Linked to value_models on a ForeignKey

    def compute_value(self):
        """Get values computted regional values of this country timely"""
        # For each value in the country, 
        # NOTE: maybe some vars could depend on average. Would work on that
        # if need be by puting total_type in parent var
        return self.regional_vars.aggregate(Sum('value'))['value__sum'] or 0
    
    @property
    def values(self):
        return self.value_models.all()



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
    inputted_value = models.DecimalField(max_digits=9, decimal_places=2, default=None)

    def computed_value(self):
        """Get sum of all values of districts in this region"""
        # NOTE: maybe some vars could depend on average. Would work on that
        # if need be by puting total_type in parent var
        return self.district_vars.aggregate(Sum('value'))['value__sum'] or 0
    
    @property
    def values(self):
        return self.variables.all()


class DistrictIndicatorVariable(models.Model):
    """District level indicator variable"""

    name = models.CharField(max_length=150)
    regional_var = models.ForeignKey(RegionalIndicatorVariable,
                                     related_name='district_vars',
                                     on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=9, decimal_places=2, default=None)

    @property
    def values(self):
        return self.variables.all()


class Indicator(models.Model):
    """The base Item in this project is the indicator"""
    
    name = models.CharField(max_length=250)
    code = models.CharField(max_length=150)
    definition = models.TextField()
    measurement_unit = models.CharField(max_length=7, choices=MeasurementUnitChoice.choices)
    aggregation_level = models.CharField(max_length=7, choices=AggregationLevelChoice.choices)
    reporting_period = models.DateField(auto_now=True)
    responsible_party = models.CharField(max_length=500)
    level = models.CharField(max_length=7, choices=MeasurementLevelChoice.choices)
    data_source = models.TextField()
    country = models.ForeignKey(Country, related_name='indicators', on_delete=models.CASCADE)
    variables = models.ManyToManyField(IndicatorVariable,
                                       related_name='indicators',
                                       blank=True)

    # def depending_vars(self):
    #     """Returns a list of variables that are used for this indicator"""
    #     return [var.name for var in self.variables.all()]

    def get_value(self, date=None):
        """
        Returns indicator values or value if date is not None
        Input:
            date -> If provided, returns indicator value at that date if
                found else None. If date is None, returns all values
        """
        if date is None:
            return self.values.all()
        
        try:
            return self.values.get(date=date)
        except ValueError:
            return None        

    def save(self, *args, **kwargs):
        """Assign indicator variables based on self.level"""
        super().save(*args, **kwargs)

        # If indicator_vars exist for the level of the country as selected,
        # link them else create them
        for var in self.variables:
            if self.level == 'Dis' and var.level in ['Nat', 'Reg']:
                var.level = self.level
                var.save()
            if self.level == 'Reg' and var.level == 'Nat':
                var.level = self.level
                var.save()
