# generate aliases
import pandas as pd
import time
import random
import openai
import traceback
import shelve
import threading
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

# Set your OpenAI API key
openai.api_key = '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'

# Global variables for throttling
lock = threading.Lock()
call_count = 0
period_start = time.time()
PERIOD = 60  # seconds

# Adjust these based on your `gpt-4` rate limits
CALLS_PER_MINUTE = 5  # Example value, adjust to your actual limit

def parse_aliases(content, known_aliases):
    additional_aliases = []
    lines = content.strip().split('\n')

    for line in lines:
        # Remove numbering or bullet points
        alias = line.strip().lstrip('-•*').lstrip('0123456789.) ').strip()
        if alias and alias.lower() not in [k.lower() for k in known_aliases]:
            additional_aliases.append(alias)
    return additional_aliases

@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=60),
    retry=retry_if_exception_type(openai.RateLimitError)
)

def generate_missing_aliases(food_item, known_aliases, cache):
    cache_key = f"{food_item}|{','.join(sorted(known_aliases))}"
    if cache_key in cache:
        print(f"Using cached aliases for {food_item}")
        return cache[cache_key]

    global call_count, period_start
    with lock:
        current_time = time.time()
        elapsed = current_time - period_start
        if elapsed >= PERIOD:
            # Reset for the new period
            period_start = current_time
            call_count = 0
        if call_count >= CALLS_PER_MINUTE:
            sleep_time = PERIOD - elapsed
            print(f"Throttling: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            period_start = time.time()
            call_count = 0
        call_count += 1

    messages = [
        {"role": "system", "content": "You are a helpful assistant that provides synonyms and aliases for food items."},
        {"role": "user", "content": f"""Food Item: {food_item}
Known Aliases: {', '.join(known_aliases)}

Task: Provide at least five additional common names, synonyms, or aliases for the food item "{food_item}" that are not included in the Known Aliases. Exclude duplicates and irrelevant terms.
"""}
    ]
    print("Messages:")
    for message in messages:
        print(f"{message['role']}: {message['content']}")
    try:
        response = openai.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
            max_completion_tokens=150,
            temperature=0.7,
            n=1,
        )
        content = response.choices[0].message['content'].strip()
        print("API Response Content:")
        print(content)
        additional_aliases = parse_aliases(content, known_aliases)
        # Store the result in cache
        cache[cache_key] = additional_aliases
        return additional_aliases
    except openai.RateLimitError as e:
        print(f"Rate limit error encountered for {food_item}: {e}")
        raise
    except Exception as e:
        print(f"Error generating aliases for {food_item}: {e}")
        traceback.print_exc()
        raise

def main():
    # Read the Excel file and specify the sheet name
    df = pd.read_excel('/Users/adrienhopkinson/Desktop/Valyant - Brain/InboundAliases(Dev).xlsx', sheet_name='filteredData')

    # **For testing, process only the first 5 rows**
    df = df.head(5)

    # Ensure the columns are correctly named
    df.rename(columns={
        'record_name': 'Food Item',
        'alias_list': 'Known Aliases'
    }, inplace=True)

    # Clean the data
    df['Food Item'] = df['Food Item'].astype(str).str.strip()
    df['Known Aliases'] = df['Known Aliases'].astype(str).fillna('').apply(
        lambda x: [alias.strip() for alias in x.split(',') if alias.strip()]
    )

    # Open a cache using shelve
    with shelve.open('alias_cache.db') as cache:
        # Generate missing aliases with caching
        df['Additional Aliases'] = df.apply(
            lambda row: generate_missing_aliases(row['Food Item'], row['Known Aliases'], cache), axis=1
        )

    # Combine known and additional aliases
    df['All Aliases'] = df.apply(
        lambda row: list(set(row['Known Aliases'] + row['Additional Aliases'])), axis=1
    )

    # Save the updated data to a new Excel file
    df.to_excel('/Users/adrienhopkinson/Desktop/updated_aliases.xlsx', index=False)

    # Print the results
    for index, row in df.iterrows():
        print(f"Food Item: {row['Food Item']}")
        print(f"Known Aliases: {row['Known Aliases']}")
        print(f"Additional Aliases: {row['Additional Aliases']}")
        print(f"All Aliases: {row['All Aliases']}")
        print('---')

if __name__ == '__main__':
    main()
