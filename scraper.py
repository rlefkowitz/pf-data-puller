import base64
import os
import pickle
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
from dotenv import load_dotenv

load_dotenv()

ZYTE_API_KEY = os.getenv("ZYTE_API_KEY")
ZYTE_CA_PATH = os.getenv("ZYTE_CA_PATH")

if not ZYTE_API_KEY:
    raise ValueError("ZYTE_API_KEY is not set in the environment variables.")

response = requests.get(
    "https://books.toscrape.com/",
    proxies={
        "http": "http://0e4b348997a84ece9a77fbca497c1302:@api.zyte.com:8011/",
        "https": "http://0e4b348997a84ece9a77fbca497c1302:@api.zyte.com:8011/",
    },
    verify="zyte-ca.crt",
)

print("Status Code:", response.status_code)

# Set up the proxies without the API key
zyte_proxies = {
    "http": f"http://{ZYTE_API_KEY}:@api.zyte.com:8011/",
    "https": f"http://{ZYTE_API_KEY}:@api.zyte.com:8011/",
}

# Make a test request
url = "https://httpbin.org/ip"

try:
    response = requests.get(url, proxies=zyte_proxies, verify="combined-ca-bundle.crt")
    print("Status Code:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Exception occurred:", e)


# Initialize the base URL, years, and teams
base_url = "https://www.pro-football-reference.com"
years = range(2017, 2024)
teams = [
    "crd",
    "atl",
    "rav",
    "buf",
    "car",
    "chi",
    "cin",
    "cle",
    "dal",
    "den",
    "det",
    "gnb",
    "htx",
    "clt",
    "jax",
    "kan",
    "rai",
    "sdg",
    "ram",
    "mia",
    "min",
    "nwe",
    "nor",
    "nyg",
    "nyj",
    "phi",
    "pit",
    "sfo",
    "sea",
    "tam",
    "oti",
    "was",
]

# Load cached high school data if available
high_schools_lock = threading.Lock()  # Lock for thread-safe access to high_schools
try:
    with open("high_schools.pkl", "rb") as f:
        high_schools = pickle.load(f)
    print("Loaded cached high school data.")
except FileNotFoundError:
    high_schools = {}
    print("No cached high school data found, starting fresh.")

# Load processed teams and years
try:
    with open("processed_teams_years.pkl", "rb") as f:
        processed_teams_years = pickle.load(f)
    print("Loaded processed teams and years.")
except FileNotFoundError:
    processed_teams_years = set()
    print("No processed teams and years found, starting fresh.")


def save_high_schools():
    with high_schools_lock:
        with open("high_schools.pkl", "wb") as f:
            pickle.dump(high_schools, f)
    print("High school data saved to cache.")


def save_processed_teams_years():
    with open("processed_teams_years.pkl", "wb") as f:
        pickle.dump(processed_teams_years, f)
    print("Processed teams and years saved to cache.")


def get_high_school(args):
    (player_url,) = args
    with high_schools_lock:
        if player_url in high_schools:
            return player_url, high_schools[player_url]
    print(f"Scraping high school info for {player_url}...")
    url = base_url + player_url
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"}

    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=zyte_proxies,
            verify="combined-ca-bundle.crt",
            timeout=30,
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            bio_section = soup.find("div", id="meta")
            if bio_section:
                high_school = None
                # Improved extraction logic
                for p in bio_section.find_all("p"):
                    strong_tag = p.find("strong")
                    if strong_tag and strong_tag.text.strip() == "High School":
                        high_school_info = ""
                        for elem in strong_tag.next_siblings:
                            if isinstance(elem, str):
                                text = elem.strip()
                                if text == ":" or text == "":
                                    continue
                                high_school_info += text + " "
                            else:
                                high_school_info += elem.get_text(strip=True) + " "
                        high_school = high_school_info.strip()
                        break
                with high_schools_lock:
                    high_schools[player_url] = high_school
                return player_url, high_school
            else:
                print(f"Bio section not found for {player_url}")
        else:
            print(f"Error scraping {player_url}: Status code {response.status_code}")
    except Exception as e:
        print(f"Exception while scraping {player_url}: {e}")
    return player_url, None


def scrape_team_roster(team, year):
    if (team, year) in processed_teams_years:
        print(f"Already processed {team} for {year}, skipping.")
        return None
    print(f"Scraping {team} for {year}...")
    url = f"{base_url}/teams/{team}/{year}_roster.htm"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"}

    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=zyte_proxies,
            verify="combined-ca-bundle.crt",
            timeout=30,
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            roster_html = None
            for comment in comments:
                if 'id="roster"' in comment:
                    roster_html = comment
                    break
            if roster_html:
                roster_soup = BeautifulSoup(roster_html, "html.parser")
                table = roster_soup.find("table", id="roster")
                if table:
                    df = pd.read_html(str(table))[0]
                    print(f"Columns found: {df.columns}")
                    df["High School"] = None

                    # Map player names to URLs
                    player_links = {}
                    for row in table.find_all("tr"):
                        player_cell = row.find("td", {"data-stat": "player"})
                        if player_cell:
                            a_tag = player_cell.find("a")
                            if a_tag:
                                player_name = a_tag.text.strip()
                                player_url = a_tag["href"]
                                player_links[player_name] = player_url

                    # Prepare arguments for multithreading
                    args_list = [
                        (player_links[player_name],)
                        for player_name in df["Player"]
                        if player_name in player_links
                    ]

                    # Use ThreadPoolExecutor for multithreading
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        future_to_player = {
                            executor.submit(get_high_school, args): args
                            for args in args_list
                        }
                        for future in as_completed(future_to_player):
                            try:
                                player_url, high_school = future.result()
                                player_name = next(
                                    (
                                        name
                                        for name, url in player_links.items()
                                        if url == player_url
                                    ),
                                    None,
                                )
                                if player_name:
                                    idx = df.index[df["Player"] == player_name].tolist()
                                    if idx:
                                        df.at[idx[0], "High School"] = high_school
                                    print(
                                        f"Player: {player_name}, High School: {high_school}"
                                    )
                            except Exception as e:
                                print(f"Exception in thread: {e}")
                            # Save high schools cache after each player
                            save_high_schools()
                    # Save DataFrame to CSV
                    file_name = f"{year}_{team}_roster.csv"
                    df.to_csv(file_name, index=False)
                    print(f"Saved {file_name}")
                    # Update processed teams and years
                    processed_teams_years.add((team, year))
                    save_processed_teams_years()
                    return file_name
                else:
                    print(f"Roster table not found for {team} in {year}")
            else:
                print(f"Could not find roster table in comments for {team} in {year}")
        else:
            print(
                f"Error scraping {team} in {year}: Status code {response.status_code}"
            )
    except Exception as e:
        print(f"Exception while scraping {team} in {year}: {e}")
    return None


def scrape_all_teams():
    all_files = []
    for team in teams:
        for year in years:
            try:
                csv_file = scrape_team_roster(team, year)
                if csv_file:
                    all_files.append(csv_file)
            except Exception as e:
                print(f"Failed to scrape {team} in {year}: {e}")
            time.sleep(
                random.uniform(1, 2)
            )  # Slight delay between team-year combinations

    # Combine and save all data
    if all_files:
        with pd.ExcelWriter("team_player_extraction.xlsx", engine="openpyxl") as writer:
            for file in all_files:
                df = pd.read_csv(file)
                sheet_name = file.replace(".csv", "")[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        print("All data saved to team_player_extraction.xlsx")


if __name__ == "__main__":
    scrape_all_teams()
