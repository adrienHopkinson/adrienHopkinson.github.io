# generate aliases
import pandas as pd
import openai

# Set your OpenAI API key
openai.api_key = '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'

def generate_missing_aliases(food_item, known_aliases):
    prompt = f"""
    Food Item: {food_item}
    Known Aliases: {', '.join(known_aliases)}

    Task: Provide additional common names, synonyms, or aliases for the food item "{food_item}" that are not included in the Known Aliases. Exclude duplicates and irrelevant terms.
    """
    print("Prompt:")
    print(prompt)
    try:
        response = openai.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=150,
            temperature=0.7,
        )
        content = response.choices[0].message['content'].strip()
        print("API Response:")
        print(content)
        additional_aliases = [alias.strip() for alias in content.split(',')]
        # Remove duplicates and aliases already in known_aliases
        additional_aliases = list(set(additional_aliases) - set(known_aliases))
        return additional_aliases
    except Exception as e:
        print(f"Error generating aliases for {food_item}: {e}")
        raise

def main():
    # Read the Excel file and specify the sheet name
    df = pd.read_excel('/Users/adrienhopkinson/Desktop/Valyant - Brain/InboundAliases(Dev).xlsx', sheet_name='filteredData')

    # Ensure the columns are correctly named
    # Replace 'Food Item' and 'Known Aliases' with your actual column names if different
    df.rename(columns={
        'record_name': 'Food Item',
        'alias_list': 'Known Aliases'
    }, inplace=True)

    # Clean the data
    df['Food Item'] = df['Food Item'].astype(str).str.strip()
    df['Known Aliases'] = df['Known Aliases'].astype(str).fillna('').apply(
        lambda x: [alias.strip() for alias in x.split(',') if alias.strip()]
    )

    # Generate missing aliases
    df['Additional Aliases'] = df.apply(
        lambda row: generate_missing_aliases(row['Food Item'], row['Known Aliases']), axis=1
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
        print(f"All Aliases: {row['All Aliases']}")
        print('---')

if __name__ == '__main__':
    main()
