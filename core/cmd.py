from dataclasses import dataclass
from typing import List


@dataclass
class Cmd:
    desc: str
    ks: List[str] = None
    group: str = None

    def __repr__(self):
        return f'{self.group}.{self.desc}'

    def __contains__(self, item):
        return self.ks and item in self.ks


class Group(type):
    def __new__(mcs, name, base, ns):
        for fn, field in ns.items():
            if isinstance(field, Cmd):
                field.group = name
        return type.__new__(mcs, name, base, ns)


class Common(metaclass=Group):
    desc = "Общее"

    QUIT = Cmd("закрыть клиент")


class Selector(metaclass=Group):
    desc = "Экран выбора эхоконференции"

    UP = Cmd("курсор вверх")
    DOWN = Cmd("курсор вниз")
    PPAGE = Cmd("страница вверх")
    NPAGE = Cmd("страница вниз")
    HOME = Cmd("в начало")
    END = Cmd("в конец")
    GET = Cmd("получить сообщения (свежие по счётчику)")
    FGET = Cmd("получить сообщения (полный индекс)")
    ARCHIVE = Cmd("переключение в архив и обратно")
    ENTER = Cmd("открыть эху")
    OUT = Cmd("исходящие сообщения")
    DRAFTS = Cmd("черновики")
    NNODE = Cmd("следующая нода")
    PNODE = Cmd("предыдущая нода")
    CONFIG = Cmd("редактировать конфиг")
    FIND = Cmd("открыть окно поиска по БД")


class Reader(metaclass=Group):
    desc = "Экран чтения сообщений"

    PREV = Cmd("предыдущее сообщение")
    NEXT = Cmd("следующее сообщение")
    PREP = Cmd("перейти ниже по цепочке ответов")
    NREP = Cmd("вернуться по цепочке ответов")
    UP = Cmd("прокрутка вверх")
    DOWN = Cmd("прокрутка вниз")
    PPAGE = Cmd("страница вверх")
    NPAGE = Cmd("страница вниз")
    UKEYS = Cmd("клавиша прокрутки или перехода к следующему сообщению")
    HOME = Cmd("в начало сообщения")
    MEND = Cmd("в конец сообщения")
    BEGIN = Cmd("в начало эхоконференции")
    END = Cmd("в конец эхоконференции")
    INS = Cmd("добавить сообщение")
    SAVE = Cmd("сохранить сообщение в файл")
    FAVORITES = Cmd("добавить сообщение в избранные")
    QUOTE = Cmd("ответить с цитированием")
    INFO = Cmd("показать msgid, адрес, тему сообщения в отдельном окне")
    LINKS = Cmd("работа со ссылками")
    GETMSG = Cmd("получить текущее сообщение с ноды")
    TO_OUT = Cmd("перенести неотправленное исходящее сообщение в черновики")
    TO_DRAFTS = Cmd("перенести черновик в исходящие сообщения")
    LIST = Cmd("список сообщений")
    INLINES = Cmd("вкл/выкл поддержку inline-оформления")
    MSUBJ = Cmd("вкл/выкл просмотр сообщений по теме")
    QUIT = Cmd("вернуться на экран выбора эхоконференции")


class Out(metaclass=Group):
    desc = "Экран просмотра исходящих и черновиков"

    EDIT = Cmd("редактировать сообщение")
    SIGN = Cmd("подписать сообщения PGP-ключом")
    DEL = Cmd("удалить черновик/исходящее/избранное")


class Qs(metaclass=Group):
    desc = "Быстрый поиск"

    OPEN = Cmd("открыть текстовое поле быстрого поиска")
    CLOSE = Cmd("прервать ввод текста")
    APPLY = Cmd("закрыть поиск оставив найденное (список сообщений, селектор эх)")

    LEFT = Cmd("курсор на символ влево")
    RIGHT = Cmd("курсор на символ вправо")
    BS = Cmd("удалить символ перед курсором")
    DEL = Cmd("удалить символ под курсором")

    HOME = Cmd("первое вхождение")
    END = Cmd("последнее вхождение")
    PREV = Cmd("предыдущее вхождение")
    NEXT = Cmd("следующее вхождение")
    PPAGE = Cmd("вхождение на предыдущей странице")
    NPAGE = Cmd("вхождение на следующей странице")
