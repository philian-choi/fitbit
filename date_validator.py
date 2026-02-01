import datetime

def get_current_date():
    return datetime.date.today().strftime("%Y-%m-%d")

def validate_search_query(query):
    current_year = datetime.date.today().year
    if str(current_year) not in query and str(current_year - 1) not in query:
        return f"{query} {current_year}"
    return query

if __name__ == "__main__":
    today = get_current_date()
    print(f"System Date Check: {today}")
    
    # Example validation
    query = "Tesla earnings"
    optimized_query = validate_search_query(query)
    print(f"Original: {query} -> Optimized: {optimized_query}")
