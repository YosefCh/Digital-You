from AI import OpenAIClient

input_file = r"C:\Users\Rebecca\OneDrive\Documents\Python AI\Wellness Tracker\food_names.txt"
alias_sql_file = r"C:\Users\Rebecca\OneDrive\Documents\Python AI\Wellness Tracker\sql\food_aliases.sql"

# THIS CODE WORKS BUT WE SHOULD CHANGE THE PROMPT TO INCLUDE THE ACTUAL NAME OF THE FOOD
# AS WELL. WE ALSO HAVE TO EXPERIMENT IF THE /n IS FROM THE PROMPT OR FROM THE END OF THE CODE
# ALSO, ISSUE WITH THE LAST COMMA, WE HAVE TO CHANGE THE CODE OR ADD A COUNT AND TELL
# AI TO LEAVE OUT THE COMMA ON THE LAST ONE. ALSO, WE SHOULD PROBABLY ADD A SEMICOLON AT THE END OF THE SQL STATEMENT
def generate_food_alias_inserts(input_file, output_sql_file):
    # Initialize OpenAI client
    ai_client = OpenAIClient(reasoning="high")
    
    aliases = []
    
    with open(output_sql_file, 'w', encoding='utf-8') as f:
        f.write("INSERT INTO food_alias (food_id, alias)\nVALUES\n")
        
    # Read food names from input file
    with open(input_file, 'r') as f:
        
        food = f.read().replace('"', '').splitlines()
        
        for i in food[1:]:  # Skip header line
            
            food_id = i.split(",")[0].strip()
            food_name = i.split(",")[1].strip()
            print(f"Generating aliases for: {food_name} (ID: {food_id})")
            
            alias_prompt = f"""
            You are generating food aliases for a nutrition tracking PostgreSQL database.

            Your task:
            Generate common aliases which can be any of the following for the provided food:

            - Common misspellings (amond for almond)
            - Singular/plural variations (apple/apples)
            - Shorthand names (pop for soda)
            - Abbreviations (if reasonable, e.g. "PB" for "peanut butter")
            - Likely user search terms (e.g. "yogurt" for "greek yogurt")

            Rules:
            - Do NOT invent new foods.
            - Do NOT generate unrelated foods.
            - Do NOT include nutritional information.
            - Keep aliases realistic and commonly typed by users.
            - Include lowercase aliases only.
            - Remove punctuation when appropriate.
            - Include common abbreviations if reasonable.
            - Include likely misspellings ONLY if common.
            - Maximum 6 aliases.
            - Minimum 2 aliases.
            - Do NOT repeat aliases. Here are the aliases you have already been used: {aliases}
            - Return ONLY SQL tuple rows.
            - Do NOT include INSERT statements.
            - Do NOT include markdown.
            - Each tuple must follow this format:

            (food_id, 'alias')

            Example:
            (42, 'greek yogurt'),\n
            (42, 'plain greek yogurt'),\n
            (42, 'greek yog'),\n
            (42, 'plain yogurt'),\n

            Food:
            food_id = {food_id}
            food_name = "{food_name}"
            """
            response = ai_client.get_response(alias_prompt)
            print(response)
            aliases.append(response)

            with open(output_sql_file, 'a') as f:
                f.write(response + ",\n")
    
generate_food_alias_inserts(input_file, alias_sql_file)