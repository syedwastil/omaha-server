from django.core.files.storage import DefaultStorage


class StorageWithSpaces(DefaultStorage):
    def get_valid_name(self, name):
        return name


storage_with_spaces_instance = StorageWithSpaces()

# Link the message and extras into a '|' separated list.
def add_extra_to_log_message(msg, extra):
    return msg + '|' + '|'.join("%s=%s" % (key, val) for (key, val) in sorted(extra.items()))

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip