import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
import re


def extract_positive_reviews_percentage(review_tooltip):
    match = re.search(r'(\d+)%', review_tooltip)
    if match:
        return match.group(1)  # Возвращаем только число процента
    return 'N/A'


def get_game_details(game_url):
    try:
        response = requests.get(game_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Проверяем является ли страница DLC к игре, если да то скип
        if soup.select_one(
                'img.category_icon[src="https://store.akamai.steamstatic.com/public/images/v6/ico/ico_dlc.png"]'):
            return None

        # Извлекаем дату выхода и форматируем
        release_date_str = soup.select_one('.release_date .date').text.strip() if soup.select_one(
            '.release_date .date') else 'N/A'
        release_date = datetime.strptime(release_date_str, '%d %b, %Y').year if release_date_str != 'N/A' else 'N/A'

        # Получаем цену и преобразуем в float
        if soup.select_one('#demoGameBtn.btn_addtocart'):
            # Если есть элемент с id demoGameBtn, получаем цену из data-price-final
            price_div = soup.select_one('.game_purchase_price.price')
            price_str = price_div['data-price-final'] if price_div else 'N/A'
        else:
            # В противном случае получаем цену из обычного места
            price_div = soup.select_one('.game_purchase_price.price')
            price_str = price_div.text.strip() if price_div else 'N/A'

        if any(phrase in price_str for phrase in ["Free To Play", "Free", "Play for Free!"]):
            price = 0.0
        else:
            try:
                price = float(price_str.replace('€', '').replace(',', '.').strip()) if price_str != 'N/A' else 'N/A'
            except ValueError:
                price = 'N/A'

        # Получаем жанры
        genres_span = soup.select_one('span[data-panel]')
        genres = [a.text.strip() for a in genres_span.select('a')] if genres_span else []
        genre = genres[0] if genres else 'N/A'

        # Извлекаем процент положительных отзывов
        review_tooltip = soup.select_one('.user_reviews_summary_row')['data-tooltip-html'] if soup.select_one(
            '.user_reviews_summary_row') else 'N/A'
        positive_reviews_percentage = extract_positive_reviews_percentage(review_tooltip)

        # Проверяем наличие внутриигровых покупок
        in_game_purchases = 1 if soup.select_one(
            'img.category_icon[src="https://store.akamai.steamstatic.com/public/images/v6/ico/ico_cart.png"]') else 0

        # Проверяем наличие наград
        awards = 1 if soup.select_one('#AwardsDefault') else 0

        # Проверяем поддержку Linux
        linux_support = 1 if soup.select_one('div.sysreq_tab[data-os="linux"]') else 0

        # Проверяем Single Player
        single_player = 1 if soup.select_one(
            'img.category_icon[src="https://store.akamai.steamstatic.com/public/images/v6/ico/ico_singlePlayer.png"]') else 0

        # Извлечение рейтинга из блока id="game_area_reviews"
        review_block = soup.select_one('#game_area_reviews')
        game_rating = None
        if review_block:
            first_br_tag = review_block.find('br')
            if first_br_tag and first_br_tag.next_sibling:
                rating_text = first_br_tag.next_sibling.strip()
                try:
                    game_rating = float(rating_text.split('/')[0])
                except (ValueError, IndexError):
                    game_rating = 0

        return release_date, price, genre, positive_reviews_percentage, in_game_purchases, awards, linux_support, single_player, game_rating

    except Exception as e:
        print(f"Error fetching details for {game_url}: {e}")
        return 'N/A', 'N/A', 'N/A', 'N/A', 0, 0, 0, 0, 0


def fetch_games_from_page(page_number):
    try:
        url = f'https://store.steampowered.com/search/results/?query&start={page_number * 20}&count=20&sort_by=Popularity_DESC'
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        games = soup.select('#search_resultsRows .search_result_row')

        if not games:
            print("No games found on this page.")
            return None

        return games
    except Exception as e:
        print(f"Error fetching games from page {page_number}: {e}")
        return None


def main():
    all_game_data = []
    page_number = 0
    max_games = 3000

    while len(all_game_data) < max_games:
        print(f"Fetching page {page_number + 1}...")
        games = fetch_games_from_page(page_number)

        if games is None:
            print("No more games found or error fetching page.")
            break

        if not games:
            print("No more games found.")
            break

        for game in games:
            if len(all_game_data) >= max_games:
                break

            # Извечение информации об игре
            game_name = game.select_one('.title').text.strip() if game.select_one('.title') else 'N/A'
            game_id = game.get('data-ds-appid', None)
            if not game_id:
                game_id = game['href'].split('/')[4]

            game_url = f'https://store.steampowered.com/app/{game_id}/'

            details = get_game_details(game_url)
            if details is None:
                continue


        print(f"Collected {len(all_game_data)} games so far.")

        page_number += 1
        time.sleep(1)

    now = datetime.now()
    date_time_str = now.strftime("%Y-%m-%d_%H-%M-%S")

    csv_filename = f"steam_games_{date_time_str}.csv"

    # Сохрани данные в CSV-файл
    if all_game_data:
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['Game Name', 'Game ID', 'Release Date', 'Price', 'Genre',
                                                      'Positive Reviews Percentage', 'In Game Purchases', 'Awards',
                                                      'Linux Support', 'Single Player', 'GM rating'])
            writer.writeheader()
            for game in all_game_data:
                writer.writerow(game)

        print(f"Data saved to {csv_filename}")
    else:
        print("No data to save.")


if __name__ == "__main__":
    main()
