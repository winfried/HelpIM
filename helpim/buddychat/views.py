from django.http import HttpResponse

def welcome(request):
    return HttpResponse('<html><body>hallo welt</body></html>')
