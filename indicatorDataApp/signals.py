from django.db.models.signals import post_save
from django.dispatch import receiver
import pycountry
from .models import Country, Region, District, Indicator
from .models import IndicatorVariable, NationalIndicatorVariable
from .models import DistrictIndicatorVariable, RegionalIndicatorVariable
from .models import AggregationLevelChoice

@receiver(post_save, sender=Country)
def create_regions(sender, instance, created, **kwargs):
    regions = pycountry.subdivisions.get(country_code=instance.code)
    if created:
        for region in regions:
            Region.objects.create(
                name=region.name,
                code=region.code,
                country=instance
            )

@receiver(post_save, sender=IndicatorVariable)
def create_indicator_vars(sender, instance, created, **kwargs):
    """
    Create indicator variables for a country, region and/or district
    Eg. if level is Nat and country is Ghana, creates the var for all
    regions in Ghana and Ghana itself
    Input:
        level -> 'c' for country, 'r' for regional and 'd' for district
        country -> country to create vars for
    """
    if instance.level == AggregationLevelChoice.NATIONAL:
        instance.get_create_national_var()
        instance.delete_regional_vars() # Would auto delete district vars, would do
                                        # nothing if regional or district vars exist not
    
    if instance.level == AggregationLevelChoice.REGIONAL:
        instance.get_create_national_var()
        instance.get_create_regional_vars()
        instance.delete_district_vars()

    if instance.level == AggregationLevelChoice.DISTRICT:
        instance.get_create_national_var()
        instance.get_create_regional_vars()
        instance.get_create_district_vars()
