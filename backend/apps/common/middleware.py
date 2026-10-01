"""
RNF-PRI-003 -- ninguna respuesta de la API queda guardada en el dispositivo del
operador salvo que la vista lo pida explicitamente.

Sin ``Cache-Control`` el navegador decide por su cuenta si guarda la respuesta
en su cache de disco (y el historial de atras/adelante), y las respuestas de la
API llevan nombres, codigos y movimientos de estudiantes menores de edad. Una
terminal de porton o de aula es compartida: lo que quede en esa cache queda en
un archivo del equipo.

Denegacion por defecto: toda respuesta bajo ``/api/`` sale con ``no-store``. La
unica excepcion es la que ya existe de forma explicita -- una vista que fija su
propio ``Cache-Control`` (los catalogos academicos de ``CacheableListMixin``,
que no contienen datos de menores) conserva el suyo.
"""

API_PATH_PREFIX = "/api/"


class NoStoreApiResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(API_PATH_PREFIX) and not response.has_header("Cache-Control"):
            response["Cache-Control"] = "no-store"
        return response
