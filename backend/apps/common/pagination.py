"""
Convencion unica de paginacion de la API (docs/ux-ui.md, seccion 1.1).

Todo listado responde el mismo sobre (`count`, `next`, `previous`, `results`)
y acepta los mismos parametros: `page` y `page_size`. Antes el backend usaba
`PageNumberPagination` sin `page_size_query_param`, asi que `?page_size=50`
se ignoraba en silencio y el selector "Filas por pagina" del frontend no
podia funcionar en ninguna tabla.

`max_page_size` acota lo que un cliente puede pedir en una sola respuesta: una
exportacion completa recorre paginas de 100 filas en vez de pedir el padron
entero de una vez.
"""

from rest_framework.pagination import PageNumberPagination

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class StandardPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_query_param = "page"
    page_size_query_param = "page_size"
    max_page_size = MAX_PAGE_SIZE
