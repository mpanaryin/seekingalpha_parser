import json
import os
from time import sleep
from typing import Optional

import requests

from googletrans import Translator
from bs4 import BeautifulSoup

from exceptions import ArticleTitleDoesNotExist, ArticleContentDoesNotExist, ArticleAlreadyExists


class ArticleStorage:
    """Класс для создания кастомного хранилища (пока просто используем файл)"""
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_file_content(self) -> list[dict]:
        """Получаем содержимое текущего файла. Если его нет возвращаем пустой список"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                file_content = json.load(f)
        else:
            file_content = []
        return file_content

    @staticmethod
    def check_exists_by_url(file_content: list[dict], url: str) -> bool:
        """Проверяем наличие статьи в файле"""
        for article in file_content:
            if article['url'] == url:
                return True
        return False

    def save(self, article: dict, file_content: Optional[list[dict]] = None) -> list[dict]:
        """
        Сохраняем статью в файл. Возвращаем новый список статей.
        Проверка на наличие самой статьи в файле вынесена в parse_process,
        чтобы её не дублировать при парсинге и при сохранении.
        """
        if not file_content:
            file_content = self.get_file_content()
        file_content.append(article)
        # Непосредственно сохранение
        json_str_result = json.dumps(file_content, ensure_ascii=False, indent=4,)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(json_str_result)
        return file_content

    def multi_save(self, articles: list[dict]):
        """
        Сохраняем список статей в файл. Возвращаем новый список статей.
        Проверка на наличие самой статьи в файле вынесена в parse_process,
        чтобы её не дублировать при парсинге и при сохранении.
        """
        file_content = self.get_file_content()
        file_content.extend(articles)
        # Непосредственно сохранение
        json_str_result = json.dumps(file_content, ensure_ascii=False, indent=4)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(json_str_result)
        return file_content


class SeekignalphaParser:
    """Парсер https://seekingalpha.com/"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    main_news_page_url = 'https://seekingalpha.com/market-news'

    @staticmethod
    def _translate(text: str, src: str = 'en', dest: str = 'ru') -> str:
        """Перевод текста"""
        translator = Translator()
        translated_text = translator.translate(text, src=src, dest=dest)
        return translated_text.text

    def get_page(self, url: str) -> str | requests.Response:
        """Получаем страницу, которую хотим парсить"""
        try:
            return requests.get(url, headers=self.headers, timeout=3)
        except requests.exceptions.Timeout as e:
            # Тут можем дописать дополнительную логику для повторного запроса
            raise e

    def parse_all_news_page(self) -> list[str]:
        """Парсим страницу со всеми новостями и вытаскиваем ссылки на новости"""
        # Получаем html
        page = self.get_page(self.main_news_page_url)
        # Разбираем страницу, чтобы могли в ней искать элементы
        soup = BeautifulSoup(page.content, 'html.parser')
        # Забираем все стати
        articles = soup.find_all('article')
        # Создаём список ссылок на статьи
        return [article.find('a')['href'] for article in articles]

    def parse_news_page(self, link: str) -> Optional[dict]:
        """Парсим конкретную страницу статьи"""
        # Формируем url
        url = f'https://seekingalpha.com{link}'
        # Получаем html
        page = self.get_page(url)
        # Разбираем страницу, чтобы могли в неё искать элементы
        soup = BeautifulSoup(page.content, 'html.parser')
        # Получаем название статьи
        article_title = soup.find('h1', attrs={'data-test-id': 'post-title'})
        # Если элемент найден, получаем название статьи, иначе получаем ошибку и идём на другую статью
        try:
            article_title = article_title.text.strip()
        except AttributeError:
            raise ArticleTitleDoesNotExist(url)
        # Получаем контейнер с параграфами статьи
        content_container = soup.find('div', attrs={'data-test-id': 'content-container'})
        # Если контейнер найден, извлекаем все теги <p> и <li> из него и формируем текст статьи.
        # Иначе вызовём ошибку и переходим на другую статью
        try:
            article_text = '\n'.join([paragraph.get_text(strip=True) for paragraph in content_container.find_all('p')])
            article_text += '\n'.join([li.get_text(strip=True) for li in content_container.find_all('li')])
        except AttributeError:
            raise ArticleContentDoesNotExist(url)
        # Если дошли до конца, то у нас есть название статьи и её текст
        return {'url': url, 'article_title': article_title, 'article_text': article_text}

    def parse_process(self):
        """Весь парсинг тут"""
        # Парсим все ссылки
        print('* Start parsing process')
        links = self.parse_all_news_page()
        # Достаём сразу весь наш файл со статьями
        storage = ArticleStorage(file_path='parsed_articles.json')
        file_content = storage.get_file_content()
        articles = []
        # Проходимся по ссылкам
        for link in links:
            # Проверяем, есть ли у нас уже эта статья
            if storage.check_exists_by_url(file_content=file_content, url=f'https://seekingalpha.com{link}'):
                continue
            # Засыпаем на N секунд. Иначе попадём в группу риска с баном или капчей.
            print('* Wait for 30 seconds')
            sleep(30)
            # Парсим статью
            try:
                news = self.parse_news_page(link)
            except (ArticleTitleDoesNotExist, ArticleContentDoesNotExist, requests.exceptions.Timeout) as e:
                # Тут можем добавить в логгер или просто print, что была ошибка
                print(e.__str__())
                continue
            # Если получилось спарсить, то обрабатываем результат
            if news:
                news['rus_article_title'] = self._translate(news['article_title'])
                news['rus_article_text'] = self._translate(news['article_text'])
                # Заполняем список статей
                articles.append(news)
                # Сохраняем сразу все статьи, которые спарсили
                storage.save(article=news)
            print('* Current parsed articles: ', articles)
        # Сохраняем сразу все статьи, которые спарсили (делаем, если не сохраняем по отдельности)
        # Можно раскомментировать нижнюю строчку, если захотим сохранять сразу все статьи, а не по отдельности.
        # storage.multi_save(articles=articles)


if __name__ == '__main__':
    parser = SeekignalphaParser()
    parser.parse_process()
