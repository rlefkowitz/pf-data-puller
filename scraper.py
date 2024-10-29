import os
import pickle
import random
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
from dotenv import load_dotenv

load_dotenv()

ZYTE_API_KEY = os.getenv("ZYTE_API_KEY")

if not ZYTE_API_KEY:
    raise ValueError("ZYTE_API_KEY is not set in the environment variables.")

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
try:
    with open("high_schools.pkl", "rb") as f:
        high_schools = pickle.load(f)
    print("Loaded cached high school data.")
except FileNotFoundError:
    high_schools = {}
    print("No cached high school data found, starting fresh.")


def get_high_school(player_url, session):
    if player_url in high_schools:
        return high_schools[player_url]
    print(f"Scraping high school info for {player_url}...")
    url = base_url + player_url
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"}
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        bio_section = soup.find("div", id="meta")
        if bio_section:
            high_school = None
            # Loop through all <p> tags in the bio section
            for p in bio_section.find_all("p"):
                strong_tag = p.find("strong")
                # Check if the <strong> tag exists and contains "High School"
                if strong_tag and strong_tag.text.strip() == "High School":
                    # Initialize an empty string to collect high school info
                    high_school_info = ""
                    # Iterate over all siblings after the <strong> tag
                    for elem in strong_tag.next_siblings:
                        if isinstance(elem, str):
                            text = elem.strip()
                            if text == ":" or text == "":
                                continue
                            high_school_info += text + " "
                        else:
                            high_school_info += elem.get_text(strip=True) + " "
                    high_school = p.get_text().split(":")[1].strip()
                    break
            high_schools[player_url] = high_school
            time.sleep(random.uniform(6, 10))  # Respect crawl delay with randomness
            return high_school
    else:
        print(f"Error scraping {player_url}: Status code {response.status_code}")
    return None


def scrape_team_roster(team, year, session):
    print(f"Scraping {team} for {year}...")
    url = f"{base_url}/teams/{team}/{year}_roster.htm"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"}
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        # The roster table is within a commented section. We need to extract and parse it.
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

                # Create a mapping from player names to URLs
                player_links = {}
                for row in table.find_all("tr"):
                    player_cell = row.find("td", {"data-stat": "player"})
                    if player_cell:
                        a_tag = player_cell.find("a")
                        if a_tag:
                            player_name = a_tag.text.strip()
                            player_url = a_tag["href"]
                            player_links[player_name] = player_url

                # Visit profile, extract high school
                for idx, row in df.iterrows():
                    player_name = row["Player"]
                    if player_name in player_links:
                        player_url = player_links[player_name]
                        high_school = get_high_school(player_url, session)
                        df.at[idx, "High School"] = high_school
                        print(f"Player: {player_name}, High School: {high_school}")
                    else:
                        print(f"Player link not found for {player_name}")
                    time.sleep(
                        random.uniform(6, 10)
                    )  # Respect crawl delay with randomness

                file_name = f"{year}_{team}_roster.csv"
                df.to_csv(file_name, index=False)
                print(f"Saved {file_name}")
                return file_name
            else:
                print(f"Roster table not found for {team} in {year}")
                return None
        else:
            print(f"Could not find roster table in comments for {team} in {year}")
            return None
    else:
        print(f"Error scraping {team} in {year}: Status code {response.status_code}")
        return None


def scrape_all_teams():
    all_files = []
    session = requests.Session()
    for team in teams:
        for year in years:
            try:
                csv_file = scrape_team_roster(team, year, session)
                if csv_file:
                    all_files.append(csv_file)
            except Exception as e:
                print(f"Failed to scrape {team} in {year}: {e}")
            time.sleep(random.uniform(6, 10))  # Respect crawl delay between teams

    # Save high schools cache
    with open("high_schools.pkl", "wb") as f:
        pickle.dump(high_schools, f)
    print("Saved high school data to cache.")

    if all_files:
        with pd.ExcelWriter("team_player_extraction.xlsx", engine="openpyxl") as writer:
            for file in all_files:
                df = pd.read_csv(file)
                sheet_name = file.replace(".csv", "")[
                    :31
                ]  # Sheet name max length is 31
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        print("All data saved to team_player_extraction.xlsx")


if __name__ == "__main__":
    scrape_all_teams()
