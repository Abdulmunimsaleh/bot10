from fastapi import FastAPI, Query
import google.generativeai as genai
from playwright.sync_api import sync_playwright
import json

# Set your Gemini API key
genai.configure(api_key="AIzaSyCpugWq859UTT5vaOe01EuONzFweYT2uUY")

app = FastAPI()

# Tidio live chat URL
tidio_chat_url = "https://www.tidio.com/panel/inbox/conversations/unassigned/"

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

# Function to ask questions using Gemini
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
    
    return answer

# Function to send message to Tidio live chat
def send_to_tidio(user_message: str):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Set headless=True if running on a server
            page = browser.new_page()
            page.goto(tidio_chat_url)
            
            # Wait for the chat input field to be visible
            page.wait_for_selector("textarea")
            
            # Type the user message
            page.fill("textarea", user_message)
            
            # Press Enter to send the message
            page.keyboard.press("Enter")
            
            browser.close()
        return True
    except Exception as e:
        print(f"Error sending message to Tidio: {e}")
        return False

@app.get("/ask")
def get_answer(question: str = Query(..., title="Question", description="Ask a question about the website")):
    answer = ask_question(question)
    
    # If the bot cannot answer or user requests live agent, transfer to support
    trigger_phrases = ["live agent", "human agent", "complaints", "refunds", "flight issues", "bookings", "problems"]
    
    if any(phrase in question.lower() for phrase in trigger_phrases) or "I cannot" in answer:
        send_to_tidio(question)
        return {"question": question, "answer": ""}  # No confirmation message
    
    return {"question": question, "answer": answer}
