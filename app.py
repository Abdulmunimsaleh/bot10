from fastapi import FastAPI, Query
import google.generativeai as genai
from playwright.sync_api import sync_playwright
import json
import requests

# Set your Gemini API key
genai.configure(api_key="AIzaSyCpugWq859UTT5vaOe01EuONzFweYT2uUY")

app = FastAPI()

# Function to scrape the website and extract content
def scrape_website(url="https://tripzoori-gittest1.fly.dev/"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("body")
        page_content = page.inner_text("body")
        
        with open("website_data.json", "w", encoding="utf-8") as f:
            json.dump({"content": page_content}, f, indent=4)
        
        browser.close()
        return page_content

# Function to load scraped data
def load_data():
    try:
        with open("website_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("content", "")
    except FileNotFoundError:
        return scrape_website()

# Function to send a message to Tidio Live Chat
def send_to_tidio(user_message):
    tidio_chat_url = "https://www.tidio.com/panel/inbox/conversations/unassigned/"
    
    payload = {
        "message": user_message,
        "source": "chatbot",
        "timestamp": "now"  # You can update this dynamically
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(tidio_chat_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return "Message sent to live agent."
    else:
        return "Failed to transfer to a live agent."

# Function to determine if a transfer is needed
def ask_question(question: str):
    data = load_data()
    
    prompt = f"""
    You are an AI assistant that answers questions based on the website content.
    Website Data: {data}
    Question: {question}
    Answer:
    """
    
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)
    answer = response.text.strip()
    
    # Define criteria for transferring to a human agent
    transfer_keywords = ["human agent", "real person", "talk to a human", "customer service"]
    cannot_answer_phrases = ["I can't do that", "I am unable", "I cannot", "I don't know", "I do not know"]
    
    if any(kw in question.lower() for kw in transfer_keywords) or any(phrase in answer.lower() for phrase in cannot_answer_phrases):
        send_to_tidio(question)  # Send the message to Tidio
        return "I have transferred you to a human agent. They will assist you shortly."

    return answer

@app.get("/ask")
def get_answer(question: str = Query(..., title="Question", description="Ask a question about the website")):
    answer = ask_question(question)
    return {"question": question, "answer": answer}
