def register_all():
    __import__('xcat3.objects.node')
    __import__('xcat3.objects.service')
    __import__('xcat3.objects.network')
    __import__('xcat3.objects.nic')
    __import__('xcat3.objects.osimage')