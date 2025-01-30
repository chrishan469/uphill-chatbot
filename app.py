import openai
import json
import re
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load API Key from .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise ValueError("API Key not found! Set OPENAI_API_KEY in .env.")

app = Flask(__name__)
CORS(app)  # Allow frontend requests

# Load knowledge base from JSON file
try:
    with open("knowledge.json", "r") as f:
        knowledge_data = json.load(f)
    print("✅ Knowledge data loaded successfully.")
except Exception as e:
    print(f"❌ Error loading knowledge.json: {e}")
    knowledge_data = {}


@app.route("/", methods=["GET"])
def home():
    return "Uphill Chatbot API is running!"


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    print(f"📩 Received message: {user_message}")

    if not user_message:
        return jsonify({"response": "Please enter a message."})

    # Retrieve relevant data including formula from the knowledge base
    relevant_info = retrieve_relevant_data(user_message)
    print(f"📊 Retrieved context: {relevant_info}")

    # Extract formula from the retrieved data (if any)
    formula_data = relevant_info.get("earnings_formula")
    if not formula_data:
        return jsonify({"response": "Sorry, I couldn't find a relevant formula for your query."})

    formula = formula_data.get("formula")
    if not formula:
        return jsonify({"response": "No formula found in the knowledge base."})

    # Attempt to compute the formula using extracted numbers
    computed_result = compute_formula(formula, user_message)

    if computed_result is not None:
        # Respond with the computed result and any additional context
        bot_reply = f"The computed result is: {computed_result}"
    else:
        bot_reply = "Sorry, I couldn't compute the result based on your query."

    # Include the knowledge data and computed results in the response
    messages = [
        {"role": "system", "content": "You are a helpful real estate assistant."},
        {"role": "system", "content": f"Company Data:\n{json.dumps(relevant_info, indent=2)}"},
        {"role": "user", "content": f"User's question: {user_message}"},
        {"role": "assistant", "content": bot_reply},
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages
        )

        bot_reply = response["choices"][0]["message"]["content"]
        print(f"🤖 ChatGPT Reply: {bot_reply}")
        return jsonify({"response": bot_reply})

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"response": "Sorry, something went wrong!"})


def retrieve_relevant_data(user_message):
    """
    Retrieves relevant data including formulas from knowledge.json
    based on the user's query.
    """
    relevant_info = {}

    # Lowercase the user's message for better matching
    message_lower = user_message.lower()

    # Search through knowledge data for relevant formula (if any)
    for key, value in knowledge_data.items():
        # Check if the key or any keyword matches in the user message
        if any(keyword.lower() in message_lower for keyword in value.get("keywords", [])):
            relevant_info[key] = value

    # Return the relevant formula if found
    if relevant_info:
        return relevant_info

    # If no formula is found, return a message saying so
    return {"info": "No exact formula found for your query."}


def compute_formula(formula, user_message):
    """
    Extracts values from the user query and evaluates the formula.
    Formula like "earnings = gci - 18000" is supported.
    """
    try:
        # Extract numbers from the user's message
        numbers = re.findall(r"(\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?)", user_message)
        if not numbers:
            return None  # If no numbers are found, return None

        # Clean extracted values (remove $ and commas)
        extracted_values = [float(num.replace(",", "").replace("$", "")) for num in numbers]

        # Assume the formula is in a form like 'earnings = gci - 18000'
        # Replace placeholders like 'gci' with actual extracted value
        formula = formula.lower()

        for value in extracted_values:
            formula = formula.replace("gci", str(value))  # Replace with actual GCI value

        # Safely evaluate the formula
        result = eval(formula, {"__builtins__": {}}, {})  # Avoid unsafe eval
        return round(result, 2)  # Return rounded result

    except Exception as e:
        print(f"⚠️ Error computing formula: {e}")
        return None  # Return None in case of error

if __name__ == "__main__":
    app.run(debug=True)
