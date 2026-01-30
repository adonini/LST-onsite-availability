from ..models import Places, Availability

def run():
    PLACES = [
            "CTAO Office"
            "Calp",
            "Holiday",
            "Holiday - Off the island"
            "ORM Day",
            "ORM Night",
            "Mirca",
            "Remote",
            "Remote - Off the island"
            ]

    for element in PLACES:
        Places.objects.get_or_create(
            name=element,
        )
    print(Places.objects.all())
    #Update the current events
    for event in Availability.objects.all():
        if isinstance(event.place_str, str):
            try:
                place = Places.objects.get(name=event.place_str)
                event.place = place
            except Places.DoesNotExist:
                pass
            try:
                shortName = event.place_str[:4]
                print(shortName)
                place = Places.objects.filter(name__icontains=shortName).first()
                print(place)
                event.place = place
            except Places.DoesNotExist:
                pass
            event.save()

