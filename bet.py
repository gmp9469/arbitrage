import requests
from datetime import datetime
import pytz

# Replace with your actual API key
API_KEY = '88db1dc6d36f8c84dd9af39d28dd9f90'

BASE_URL = 'https://api.the-odds-api.com/v4/sports/'

# Set the parameters for the request
sport = 'upcoming'  # NFL as an example
region = 'us'  # US region
markets = 'h2h,totals'  # Head-to-head and totals (over/under) markets
odds_format = 'american'  
date_format = 'iso'  

# List of bookmakers to exclude
excluded_bookmakers = ['betonlineag', 'bovada', 'lowvig', 'mybookieag', 'superbook', 'wynnbet', 'unibet_us']

url = f'{BASE_URL}{sport}/odds/?apiKey={API_KEY}&regions={region}&markets={markets}&oddsFormat={odds_format}&dateFormat={date_format}'

response = requests.get(url)

def american_to_decimal(odds):
    if odds > 0:
        return odds / 100 + 1
    else:
        return 100 / abs(odds) + 1

def convert_utc_to_est(utc_time_str):
    utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ')
    utc_zone = pytz.utc
    est_zone = pytz.timezone('US/Eastern')
    utc_time = utc_zone.localize(utc_time)
    est_time = utc_time.astimezone(est_zone)
    return est_time.strftime('%Y-%m-%d %I:%M %p %Z')

def calculate_arbitrage_percentage(odds_1, odds_2):
    dec_odds_1 = american_to_decimal(odds_1)
    dec_odds_2 = american_to_decimal(odds_2)
    arbitrage_percentage = (1 / dec_odds_1) + (1 / dec_odds_2)
    
    return arbitrage_percentage

def calculate_arbitrage(odds_1, odds_2, total_bet=100):
    dec_odds_1 = american_to_decimal(odds_1)
    dec_odds_2 = american_to_decimal(odds_2)
    
    bet_1 = (total_bet * dec_odds_2) / (dec_odds_1 + dec_odds_2)
    bet_2 = total_bet - bet_1
    
    profit_outcome_1 = (bet_1 * dec_odds_1) - total_bet
    profit_outcome_2 = (bet_2 * dec_odds_2) - total_bet
    
    return bet_1, bet_2, profit_outcome_1, profit_outcome_2

if response.status_code == 200:
    odds_data = response.json()
    arbitrage_opportunities = []  

    for event in odds_data:
        game_id = event['id']
        home_team = event['home_team']
        away_team = event['away_team']
        game_date_utc = event['commence_time']  
        sport = event['sport_key']  
        bookmakers = event['bookmakers']
        
        game_date_est = convert_utc_to_est(game_date_utc)
        
        best_h2h_home_odds = None
        best_h2h_away_odds = None
        best_totals_over_odds = None
        best_totals_under_odds = None
        best_h2h_home_bookmaker = None
        best_h2h_away_bookmaker = None
        best_totals_over_bookmaker = None
        best_totals_under_bookmaker = None
        best_totals_point = None  

        for bookmaker in bookmakers:
            if bookmaker['key'] in excluded_bookmakers:
                continue  

            for market in bookmaker['markets']:
                if len(market['outcomes']) != 2:
                    continue  

                if market['key'] == 'h2h':  
                    for outcome in market['outcomes']:
                        if outcome['name'] == home_team:
                            if best_h2h_home_odds is None or outcome['price'] > best_h2h_home_odds:
                                best_h2h_home_odds = outcome['price']
                                best_h2h_home_bookmaker = bookmaker['title']
                        if outcome['name'] == away_team:
                            if best_h2h_away_odds is None or outcome['price'] > best_h2h_away_odds:
                                best_h2h_away_odds = outcome['price']
                                best_h2h_away_bookmaker = bookmaker['title']
                
                if market['key'] == 'totals': 
                    over = None
                    under = None
                    for outcome in market['outcomes']:
                        if outcome['name'] == 'Over':
                            over = outcome
                        if outcome['name'] == 'Under':
                            under = outcome
                    
                    if over and under and over['point'] == under['point']:
                        if best_totals_over_odds is None or over['price'] > best_totals_over_odds:
                            best_totals_over_odds = over['price']
                            best_totals_over_bookmaker = bookmaker['title']
                            best_totals_point = over['point']  
                        if best_totals_under_odds is None or under['price'] > best_totals_under_odds:
                            best_totals_under_odds = under['price']
                            best_totals_under_bookmaker = bookmaker['title']
                            best_totals_point = under['point']  
        
        if best_h2h_home_odds and best_h2h_away_odds:
            arbitrage_percentage = calculate_arbitrage_percentage(best_h2h_home_odds, best_h2h_away_odds)

            if arbitrage_percentage < 1:
                bet_1, bet_2, profit_team_1, profit_team_2 = calculate_arbitrage(best_h2h_home_odds, best_h2h_away_odds)
                arbitrage_opportunities.append({
                    "type": "h2h",
                    "sport": sport,
                    "game": f"{home_team} vs {away_team}",
                    "date": game_date_est,  
                    "best_home_odds": best_h2h_home_odds,
                    "best_home_bookmaker": best_h2h_home_bookmaker,
                    "best_away_odds": best_h2h_away_odds,
                    "best_away_bookmaker": best_h2h_away_bookmaker,
                    "bet_1": bet_1,
                    "bet_2": bet_2,
                    "profit_team_1": profit_team_1,
                    "profit_team_2": profit_team_2,
                    "min_profit": min(profit_team_1, profit_team_2),
                    "max_profit": max(profit_team_1, profit_team_2)
                })

        if best_totals_over_odds and best_totals_under_odds and best_totals_point:
            arbitrage_percentage = calculate_arbitrage_percentage(best_totals_over_odds, best_totals_under_odds)

            if arbitrage_percentage < 1:
                bet_1, bet_2, profit_over, profit_under = calculate_arbitrage(best_totals_over_odds, best_totals_under_odds)
                arbitrage_opportunities.append({
                    "type": "totals",
                    "sport": sport,
                    "game": f"{home_team} vs {away_team}",
                    "date": game_date_est,  
                    "best_over_odds": best_totals_over_odds,
                    "best_over_bookmaker": best_totals_over_bookmaker,
                    "best_under_odds": best_totals_under_odds,
                    "best_under_bookmaker": best_totals_under_bookmaker,
                    "best_point_line": best_totals_point,  
                    "bet_1": bet_1,
                    "bet_2": bet_2,
                    "profit_over": profit_over,
                    "profit_under": profit_under,
                    "min_profit": min(profit_over, profit_under),
                    "max_profit": max(profit_over, profit_under)
                })
    
    arbitrage_opportunities.sort(key=lambda x: x['min_profit'])

    if len(arbitrage_opportunities) == 0:
        print("No opportunites")
    for arb in arbitrage_opportunities:
        if arb['type'] == 'h2h':
            print(f"Sport: {arb['sport']}")
            print(f"H2H Game: {arb['game']} on {arb['date']}")
            print(f"Best Home Team Odds: {arb['best_home_odds']} (from {arb['best_home_bookmaker']})")
            print(f"Best Away Team Odds: {arb['best_away_odds']} (from {arb['best_away_bookmaker']})")
            print(f"Bet ${arb['bet_1']:.2f} on the home team and ${arb['bet_2']:.2f} on the away team.")
            print(f"Profit Range: ${arb['min_profit']:.2f} to ${arb['max_profit']:.2f}")
            print("\n")
        elif arb['type'] == 'totals':
            print(f"Sport: {arb['sport']}")
            print(f"Totals Game: {arb['game']} on {arb['date']}")
            print(f"Best Over Odds: {arb['best_over_odds']} (from {arb['best_over_bookmaker']}) at point line {arb['best_point_line']}")
            print(f"Best Under Odds: {arb['best_under_odds']} (from {arb['best_under_bookmaker']}) at point line {arb['best_point_line']}")
            print(f"Bet ${arb['bet_1']:.2f} on the over and ${arb['bet_2']:.2f} on the under.")
            print(f"Profit Range: ${arb['min_profit']:.2f} to ${arb['max_profit']:.2f}")
            print("\n")
else:
    print(f"Error fetching data: {response.status_code}")
