from collections import Sequence


# https://docs.pylonsproject.org/projects/pyramid-cookbook/en/latest/views/conditional_http.html
def conditional_http_tween_factory(handler, registry):
    def conditional_http_tween(request):
        response = handler(request)

        # If the Last-Modified header has been set, we want to enable the
        # conditional response processing.
        if response.last_modified is not None:
            response.conditional_response = True

        # We want to only enable the conditional machinery if either we
        # were given an explicit ETag header by the view or we have a
        # buffered response and can generate the ETag header ourself.
        if response.etag is not None:
            response.conditional_response = True
        elif (isinstance(response.app_iter, Sequence) and
                len(response.app_iter) == 1):
            response.conditional_response = True
            response.md5_etag()

        return response
    return conditional_http_tween
