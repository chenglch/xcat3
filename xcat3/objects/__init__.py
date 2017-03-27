def register_all():
    __import__('xcat3.objects.node')
    __import__('xcat3.objects.conductor')
    __import__('xcat3.objects.network')
    __import__('xcat3.objects.nics')