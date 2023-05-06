from geopy.geocoders import Nominatim

# geolocator = Nominatim(user_agent="geoapiExercises")

# def get_districts(country):
#     location = geolocator.geocode(country)
#     print(location.address)
#     return location.raw['address']['state_district']

# print(get_districts("United States"))

# from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="my_app")

# replace 'Nigeria' with the name of the country you want to get regions for
location = geolocator.geocode("Nigeria", exactly_one=True)

if location:
    print(location.raw['address'])
else:
    print('Could not find the location')
