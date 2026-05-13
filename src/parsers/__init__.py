from .santander import parse_file as parse_santander
from .banco_do_brasil import parse_file as parse_banco_do_brasil
from .sicoob import parse_file as parse_sicoob
from .bradesco_comprovante import parse_file as parse_bradesco_comprovante
from .itau_comprovante import parse_file as parse_itau_comprovante

__all__ = [
    "parse_santander",
    "parse_banco_do_brasil",
    "parse_sicoob",
    "parse_bradesco_comprovante",
    "parse_itau_comprovante",
]
