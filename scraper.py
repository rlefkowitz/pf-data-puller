import os
import pickle
import queue
import threading
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

# Set up the proxies without the API key
zyte_proxies = {
    "http": f"http://{ZYTE_API_KEY}:@api.zyte.com:8011/",
    "https": f"http://{ZYTE_API_KEY}:@api.zyte.com:8011/",
}

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

player_queue = queue.Queue()

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


def get_high_school():
    while True:
        try:
            player_url = player_queue.get(timeout=5)
        except queue.Empty:
            break

        with high_schools_lock:
            if player_url in high_schools and high_schools[player_url] is not None:
                player_queue.task_done()
                continue

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
                    print(f"Updated high school for {player_url}: {high_school}")
                else:
                    print(f"Bio section not found for {player_url}")
            else:
                print(
                    f"Error scraping {player_url}: Status code {response.status_code}"
                )
        except Exception as e:
            print(f"Exception while scraping {player_url}: {e}")
        finally:
            save_high_schools()
            player_queue.task_done()


def scrape_team_roster(team, year):
    file_name = f"{year}_{team}_roster.csv"
    if (team, year) in processed_teams_years:
        print(f"Already processed {team} for {year}, skipping.")
        # Return the existing CSV file name if it exists
        if os.path.exists(file_name):
            return file_name
        else:
            print(f"CSV file {file_name} not found for {team} in {year}.")
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

                    # Add "Player URL" column to the DataFrame
                    df["Player URL"] = df["Player"].map(player_links)

                    # Enqueue uncached or None-valued players
                    for player_name, player_url in player_links.items():
                        with high_schools_lock:
                            if (
                                player_url not in high_schools
                                or high_schools[player_url] is None
                            ):
                                player_queue.put(player_url)

                    # Update processed teams and years
                    processed_teams_years.add((team, year))
                    save_processed_teams_years()

                    # Save DataFrame to CSV
                    file_name = f"{year}_{team}_roster.csv"
                    df.to_csv(file_name, index=False)
                    print(f"Saved {file_name}")
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
    max_workers = 16

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as team_executor, ThreadPoolExecutor(max_workers=max_workers) as player_executor:

        # Start player data fetching threads
        for _ in range(max_workers):
            player_executor.submit(get_high_school)

        # Submit team scraping tasks
        team_futures = []
        for team in teams:
            for year in years:
                future = team_executor.submit(scrape_team_roster, team, year)
                team_futures.append(future)

        # Wait for all team scraping tasks to complete
        for future in as_completed(team_futures):
            try:
                csv_file = future.result()
                if csv_file:
                    all_files.append(csv_file)
            except Exception as e:
                print(f"Exception in team scraping: {e}")

        # Wait for the player queue to be fully processed
        player_queue.join()
        print("All high school data fetched.")

    # Remove duplicates from all_files
    all_files = list(set(all_files))

    # Update CSV files with high school data
    for file_name in all_files:
        if os.path.exists(file_name):
            df = pd.read_csv(file_name)
            # Ensure 'Player URL' and 'High School' columns exist
            if "Player URL" in df.columns and "High School" in df.columns:
                # Update 'High School' column using 'Player URL' and 'high_schools' cache
                for idx, row in df.iterrows():
                    player_url = row["Player URL"]
                    if pd.notna(player_url):
                        with high_schools_lock:
                            high_school = high_schools.get(player_url)
                        df.at[idx, "High School"] = high_school
                # Save the updated DataFrame to CSV
                df.to_csv(file_name, index=False)
                print(f"Updated {file_name} with high school data.")
            else:
                print(f"'Player URL' or 'High School' column missing in {file_name}.")
        else:
            print(f"CSV file {file_name} not found.")

    # Combine and save all data
    if all_files:
        with pd.ExcelWriter("team_player_extraction.xlsx", engine="openpyxl") as writer:
            for file in all_files:
                if os.path.exists(file):
                    df = pd.read_csv(file)
                    sheet_name = file.replace(".csv", "")[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    print(f"CSV file {file} not found.")
            print("All data saved to team_player_extraction.xlsx")
    else:
        print("No CSV files to combine.")


if __name__ == "__main__":
    scrape_all_teams()
