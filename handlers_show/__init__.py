from aiogram import Router
import logging


# 1. Сначала создаем роутер
router = Router()
logger = logging.getLogger(__name__)

# 2. Затем импортируем хендлеры из всех подмодулей
from .handlers_want_talk import *
from .handlers_body import *
from .handlers_rela import *
from .handlers_sex import *
from .handlers import *
from .handlers_admin import *
from .handlers_stream import *
from .promokode_hd import *
from .handlers_pie import *


# 3. Указываем что экспортируем
__all__ = ['router']

