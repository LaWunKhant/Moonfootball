import httpx
import re
import json
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os


class UnderstatDataScraper:
    def __init__(self, team_name="Arsenal"):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.base_url = "https://understat.com"
        self.team_name = team_name

        # Map common team names to Understat URL format
        self.team_url_mapping = {
            "Arsenal": "Arsenal",
            "Manchester United": "Manchester_United",
            "Manchester City": "Manchester_City",
            "Liverpool": "Liverpool",
            "Chelsea": "Chelsea",
            "Tottenham": "Tottenham",
            "Newcastle": "Newcastle_United",
            "Brighton": "Brighton",
            "Aston Villa": "Aston_Villa",
            "West Ham": "West_Ham",
            "Crystal Palace": "Crystal_Palace",
            "Fulham": "Fulham",
            "Wolves": "Wolverhampton_Wanderers",
            "Everton": "Everton",
            "Brentford": "Brentford",
            "Nottingham Forest": "Nottingham_Forest",
            "Luton": "Luton",
            "Burnley": "Burnley",
            "Sheffield United": "Sheffield_United",
            "Bournemouth": "Bournemouth"
        }

        # Get the URL-safe team name
        self.team_url = self.team_url_mapping.get(team_name, team_name.replace(" ", "_"))

    def create_data_directory(self):
        """Create data directory if it doesn't exist"""
        if not os.path.exists("data"):
            os.makedirs("data")
            print("📁 Created data directory")

    def fetch_with_httpx(self, season="2024"):
        """Method 1: Try to fetch with httpx (faster)"""
        # Fixed: Use self.team_url instead of hardcoded "Arsenal"
        url = f"{self.base_url}/team/{self.team_url}/{season}"
        print(f"🔍 Trying to fetch {self.team_name} data for {season} season...")

        try:
            response = httpx.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            html = response.text

            # Try multiple possible patterns for match data (updated for new structure)
            patterns = [
                # New patterns based on debug output
                r"var statisticsData\s*=\s*JSON\.parse\('([^']+)'\);",
                r"var datesData\s*=\s*JSON\.parse\('([^']+)'\);",
                r"var playersData\s*=\s*JSON\.parse\('([^']+)'\);",

                # Original patterns (keep as fallback)
                r"var matchesData\s*=\s*JSON\.parse\('([^']+)'\);",
                r"var matchesData\s*=\s*JSON\.parse\(\"([^\"]+)\"\);",
                r"var matchesData\s*=\s*(\[.*?\]);",

                # Generic patterns for any data
                r"var\s+(\w*[Dd]ata\w*)\s*=\s*JSON\.parse\('([^']+)'\);",
            ]

            for i, pattern in enumerate(patterns):
                print(f"   Trying pattern {i + 1}...")
                match = re.search(pattern, html, re.DOTALL)

                if match:
                    print(f"✅ Found data with pattern {i + 1}")
                    try:
                        # Handle the generic pattern differently (it has 2 groups)
                        if i == 6:  # Generic pattern with variable name
                            var_name = match.group(1)
                            raw_json = match.group(2).encode().decode("unicode_escape")
                            print(f"   Found variable: {var_name}")
                            data = json.loads(raw_json)
                        elif i == 5:  # Direct JSON array
                            data = json.loads(match.group(1))
                        else:
                            raw_json = match.group(1).encode().decode("unicode_escape")
                            data = json.loads(raw_json)

                        # Check if this looks like match data
                        if self.is_match_data(data):
                            print(f"   ✅ This appears to be match data!")
                            return self.process_match_data(data, season)
                        else:
                            print(f"   ⚠️ Data found but doesn't look like match data")
                            # Save for debugging
                            self.save_debug_data(data, f"debug_data_pattern_{i + 1}.json")
                            continue

                    except json.JSONDecodeError as e:
                        print(f"   ❌ JSON decode error with pattern {i + 1}: {e}")
                        continue

            # If no patterns work, try to extract all data variables
            print("🔍 Searching for any JSON structures in the page...")
            potential_data = self.extract_all_data_variables(html)
            if potential_data:
                return self.process_match_data(potential_data, season)

            # Final fallback - analyze page content
            self.debug_page_content(html)
            return None

        except Exception as e:
            print(f"❌ httpx method failed: {e}")
            return None

    def fetch_with_selenium(self, season="2024"):
        """Method 2: Use Selenium as fallback"""
        print("🤖 Falling back to Selenium method...")

        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--user-agent={self.headers['User-Agent']}")

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            url = f"{self.base_url}/team/{self.team_url}/{season}"
            driver.get(url)

            # Wait for JavaScript to load
            time.sleep(5)

            # Get page source after JS execution
            html = driver.page_source
            driver.quit()

            # Try to extract all data variables
            potential_data = self.extract_all_data_variables(html)
            if potential_data:
                return self.process_match_data(potential_data, season)

            print("❌ Selenium method also failed to find match data")
            return None

        except Exception as e:
            print(f"❌ Selenium method failed: {e}")
            return None

    def is_match_data(self, data):
        """Check if the data looks like match data"""
        if not data:
            return False

        # If it's a list of dictionaries, check the first item
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                # Look for common match data fields - updated based on your actual data structure
                match_fields = ['goals', 'xG', 'result', 'datetime', 'side', 'h', 'a']
                found_fields = sum(1 for field in match_fields if field in first_item.keys())
                return found_fields >= 3  # At least 3 match-related fields

        # If it's a dictionary, it might be match data if it has match-like keys
        if isinstance(data, dict):
            match_fields = ['goals', 'xG', 'result', 'datetime', 'side', 'h', 'a']
            found_fields = sum(1 for field in match_fields if field in data.keys())
            return found_fields >= 3

        return False

    def save_debug_data(self, data, filename):
        """Save data for debugging purposes"""
        try:
            debug_path = f"data/debug_{filename}"
            with open(debug_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"   📝 Saved debug data to {debug_path}")
        except Exception as e:
            print(f"   ❌ Could not save debug data: {e}")

    def extract_all_data_variables(self, html):
        """Extract all JavaScript data variables for analysis"""
        print("\n🔍 ADVANCED DEBUG: Extracting all data variables...")

        # Find all var declarations with JSON.parse
        pattern = r"var\s+(\w+)\s*=\s*JSON\.parse\('([^']+)'\);"
        matches = re.findall(pattern, html)

        extracted_data = {}
        for var_name, json_str in matches:
            try:
                raw_json = json_str.encode().decode("unicode_escape")
                data = json.loads(raw_json)
                extracted_data[var_name] = data

                print(
                    f"   ✅ Extracted {var_name}: {type(data)} with {len(data) if hasattr(data, '__len__') else 'N/A'} items")

                # Save each variable for inspection
                self.save_debug_data(data, f"{var_name}.json")

                # Check if this could be match data
                if self.is_match_data(data):
                    print(f"   🎯 {var_name} looks like match data!")
                    return data

            except Exception as e:
                print(f"   ❌ Could not parse {var_name}: {e}")

        return None

    def debug_page_content(self, html):
        """Debug method to analyze page content"""
        print("\n🔍 DEBUG: Analyzing page content...")

        # Look for any JavaScript variables
        js_vars = re.findall(r'var\s+(\w+)\s*=', html)
        print(f"   Found JS variables: {set(js_vars)}")

        # Look for JSON.parse calls
        json_parse_calls = re.findall(r'JSON\.parse\([^)]+\)', html)
        print(f"   Found {len(json_parse_calls)} JSON.parse calls")

        # Look for team-related data
        team_mentions = len(re.findall(rf'{self.team_name}', html, re.IGNORECASE))
        print(f"   '{self.team_name}' mentioned {team_mentions} times")

        # Check if this might be a different page structure
        if "understat.com" in html and team_mentions > 0:
            print(f"   ✅ This appears to be a valid Understat {self.team_name} page")
            print("   💡 The data structure may have changed")
        else:
            print("   ❌ This doesn't appear to be the expected page")

    def process_match_data(self, data, season):
        """Process the scraped match data to match your desired CSV format"""
        if not data:
            print("❌ No data to process")
            return None

        print(f"✅ Processing {len(data)} matches...")

        # Create a proper copy of the DataFrame to avoid SettingWithCopyWarning
        df = pd.DataFrame(data).copy()
        print(f"   Original columns found: {list(df.columns)}")

        # Process the data step by step
        processed_data = []

        for idx, row in df.iterrows():
            match_info = {}

            # Convert and format date
            try:
                if row.get('datetime'):
                    # Convert datetime to YYYY-MM-DD format
                    date_obj = pd.to_datetime(row.get('datetime'))
                    match_info['date'] = date_obj.strftime('%Y-%m-%d')
                else:
                    match_info['date'] = None
            except:
                match_info['date'] = None

            # Determine if the selected team was home or away
            team_side = row.get('side', 'h')  # Default to home if not specified
            match_info['h_a'] = team_side

            # Extract team names from nested dictionaries
            home_team_data = row.get('h', {})
            away_team_data = row.get('a', {})

            # Get team names, handling both dict and string formats
            if isinstance(home_team_data, dict):
                home_team = home_team_data.get('title', 'Unknown')
            else:
                home_team = str(home_team_data) if home_team_data else 'Unknown'

            if isinstance(away_team_data, dict):
                away_team = away_team_data.get('title', 'Unknown')
            else:
                away_team = str(away_team_data) if away_team_data else 'Unknown'

            # Replace team names with shorter versions for better display
            team_name_mapping = {
                'Nottingham Forest': 'Forest',
                'Manchester United': 'Man United',
                'Manchester City': 'Man City',
                'Tottenham': 'Spurs',
                'Newcastle United': 'Newcastle',
                'West Ham United': 'West Ham',
                'Aston Villa': 'Villa',
                'Brighton & Hove Albion': 'Brighton',
                'Crystal Palace': 'Palace',
                'Sheffield United': 'Sheffield Utd',
                'Wolverhampton Wanderers': 'Wolves'
            }

            # Apply team name mapping
            home_team = team_name_mapping.get(home_team, home_team)
            away_team = team_name_mapping.get(away_team, away_team)

            match_info['team_h'] = home_team
            match_info['team_a'] = away_team

            # Extract goals from team's perspective with better error handling
            goals = row.get('goals', {})
            if isinstance(goals, dict) and 'h' in goals and 'a' in goals:
                try:
                    home_goals = int(goals['h'])
                    away_goals = int(goals['a'])

                    if team_side == 'h':
                        # Team was home
                        match_info['goals_for'] = home_goals
                        match_info['goals_against'] = away_goals
                    else:
                        # Team was away
                        match_info['goals_for'] = away_goals
                        match_info['goals_against'] = home_goals
                except (ValueError, TypeError):
                    match_info['goals_for'] = 0
                    match_info['goals_against'] = 0
            else:
                match_info['goals_for'] = 0
                match_info['goals_against'] = 0

            # Extract xG from team's perspective with better error handling
            xg_data = row.get('xG', {})
            if isinstance(xg_data, dict) and 'h' in xg_data and 'a' in xg_data:
                try:
                    home_xg = float(xg_data['h'])
                    away_xg = float(xg_data['a'])

                    if team_side == 'h':
                        # Team was home
                        xg_for = home_xg
                        xg_against = away_xg
                    else:
                        # Team was away
                        xg_for = away_xg
                        xg_against = home_xg

                    # Round to 1 decimal place like your example
                    match_info['xG_for'] = round(xg_for, 1)
                    match_info['xG_against'] = round(xg_against, 1)
                except (ValueError, TypeError):
                    match_info['xG_for'] = 0.0
                    match_info['xG_against'] = 0.0
            else:
                match_info['xG_for'] = 0.0
                match_info['xG_against'] = 0.0

            # Add xGA (Expected Goals Against) - same as xG_against but rounded to 1 decimal
            match_info['xGA'] = match_info['xG_against']

            # Calculate correct result based on goals
            if match_info['goals_for'] > match_info['goals_against']:
                match_info['result'] = 'w'
            elif match_info['goals_for'] < match_info['goals_against']:
                match_info['result'] = 'l'
            else:
                match_info['result'] = 'd'

            processed_data.append(match_info)

        # Create new DataFrame with processed data
        df_clean = pd.DataFrame(processed_data)

        # Set exact column order to match your desired format
        column_order = [
            'date', 'h_a', 'team_h', 'team_a', 'goals_for',
            'goals_against', 'xG_for', 'xG_against', 'xGA', 'result'
        ]

        # Only include columns that exist and in the right order
        df_clean = df_clean[[col for col in column_order if col in df_clean.columns]]

        # Save to CSV - Fixed: Use generic filename instead of hardcoded "arsenal"
        team_filename = self.team_name.lower().replace(" ", "_")
        filename = f"data/{team_filename}_matches_{season}.csv"
        df_clean.to_csv(filename, index=False)
        print(f"✅ Saved {len(df_clean)} matches to {filename}")

        print(f"\n📊 Sample data for {self.team_name} (matching your desired format):")
        print(df_clean.head())

        # Show some basic stats
        wins = len(df_clean[df_clean['result'] == 'w'])
        draws = len(df_clean[df_clean['result'] == 'd'])
        losses = len(df_clean[df_clean['result'] == 'l'])
        print(f"\n📈 Season Summary: {wins}W-{draws}D-{losses}L")

        return df_clean

    def fetch_current_season_data(self):
        """Try to fetch current season data"""
        current_season = "2024"

        # Try httpx first
        result = self.fetch_with_httpx(current_season)

        # If that fails, try Selenium
        if result is None:
            result = self.fetch_with_selenium(current_season)

        # If still no luck, try previous season
        if result is None:
            print("🔄 Trying previous season (2023)...")
            result = self.fetch_with_httpx("2023")
            if result is None:
                result = self.fetch_with_selenium("2023")

        return result

    def run(self):
        """Main method to run the scraper"""
        print(f"🚀 Starting {self.team_name} Data Scraper...")
        self.create_data_directory()

        result = self.fetch_current_season_data()

        if result is not None:
            print(f"\n✅ SUCCESS: {self.team_name} match data has been scraped and saved!")
            return result
        else:
            print(f"\n❌ FAILED: Could not scrape {self.team_name} match data")
            print("💡 Possible solutions:")
            print("   - Check if Understat.com is accessible")
            print("   - The website structure may have changed")
            print("   - Try running the script again later")
            print("   - Consider using an alternative data source")
            return None


def fetch_team_data(team_name="Arsenal"):
    """Main function to fetch data for any team"""
    scraper = UnderstatDataScraper(team_name)
    return scraper.run()


def fetch_arsenal_data():
    """Maintain backward compatibility"""
    return fetch_team_data("Arsenal")


if __name__ == "__main__":
    # Example usage - you can change the team here
    team = "Chelsea"  # Change this to any Premier League team
    fetch_team_data(team)