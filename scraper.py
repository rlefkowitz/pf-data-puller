import os
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

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
high_schools = {}


def setup_selenium():
    chrome_options = Options()
    # chrome_options.add_argument("--headless" )
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )
    return driver


def get_high_school(driver, player_url):
    print(f"Scraping high school info for {player_url}...")
    if player_url in high_schools:
        return high_schools[player_url]
    url = base_url + player_url
    driver.get(url)

    try:
        bio_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "meta"))
        )
        if bio_section:
            high_school = None
            for p in bio_section.find_all("p"):
                p_text = p.get_text()
                if "High School" in p_text:
                    high_school = p_text.split(":")[1].strip()
                    break
            high_schools[player_url] = high_school
            return high_school
        return None
    except Exception as e:
        print(f"Error scraping {player_url}: {e}")
        return None


def scrape_team_roster(driver, team, year):
    print(f"Scraping {team} for {year}...")
    url = f"{base_url}/teams/{team}/{year}_roster.htm"
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "all_roster"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")

        all_roster_div = soup.find("div", id="all_roster")
        table = all_roster_div.find("table", id="roster")

        if table:
            df = pd.read_html(str(table))[0]

            print(df.columns)

            df["High School"] = None

            # visit profile, extract high school
            for idx, row in df.iterrows():
                player_tag = table.find("a", text=row["Player"])
                if player_tag:
                    player_url = player_tag["href"]
                    high_school = get_high_school(driver, player_url)
                    df.at[idx, "High School"] = high_school
                    print(f"Player: {row['Player']}, High School: {high_school}")

                    time.sleep(1)

            file_name = f"{year}_{team}_roster.csv"
            df.to_csv(file_name, index=False)
            print(f"Saved {file_name}")
            return file_name
        else:
            print(f"Roster table not found for {team} in {year}")
            return None
    except Exception as e:
        print(f"Error scraping {team} in {year}: {e}")
        return None


def scrape_all_teams():
    driver = setup_selenium()
    all_files = []

    for team in teams:
        for year in years:
            print(f"Scraping {team} for {year}...")
            try:
                csv_file = scrape_team_roster(driver, team, year)
                if csv_file:
                    all_files.append(csv_file)
            except Exception as e:
                print(f"Failed to scrape {team} in {year}: {e}")

    if all_files:
        with pd.ExcelWriter("team_player_extraction.xlsx", engine="openpyxl") as writer:
            for file in all_files:
                df = pd.read_csv(file)
                df.to_excel(writer, sheet_name=file.split(".")[0], index=False)
        print("All data saved to team_player_extraction.xlsx")


if __name__ == "__main__":
    scrape_all_teams()
