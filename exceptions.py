class ParseError(Exception):
    """Базовая ошибка парсинга"""
    def __init__(self, message: str | None = None) -> None:
        if not message:
            message = 'Общая ошибка парсинга'
        super().__init__(message)


class ArticleTitleDoesNotExist(AttributeError):
    def __init__(self, article_url: str, message: str | None = None) -> None:
        if not message:
            message = f'Не найдено название статьи. URL: {article_url}'
        super().__init__(message)


class ArticleContentDoesNotExist(AttributeError):
    def __init__(self, article_url: str, message: str | None = None) -> None:
        if not message:
            message = f'Не найден текст статьи. URL: {article_url}'
        super().__init__(message)


class ArticleAlreadyExists(Exception):
    def __init__(self, article_url: str, message: str | None = None) -> None:
        if not message:
            message = f'Статья уже была обработана и сохранена. URL: {article_url}'
        super().__init__(message)
