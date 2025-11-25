#!/usr/bin/env python3
"""
Update portfolio weights from BullAware
Run this periodically (weekly/monthly) to keep weights current
"""
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def fetch_portfolio_weights_selenium():
    """Fetch portfolio weights using Selenium"""
    weights = {}
    
    driver = webdriver.Chrome()  # or Firefox()
    try:
        # Navigate to BullAware portfolio page
        driver.get("https://bullaware.com/etoro/AndreaRavalli")
        time.sleep(3)  # Wait for page load
        
        # Find all elements with portfolio value percentages
        # This will need adjustment based on actual HTML structure
        elements = driver.find_elements(By.CSS_SELECTOR, "[data-portfolio-value]")
        
        for elem in elements:
            ticker = elem.get_attribute("data-ticker")
            weight = float(elem.get_attribute("data-portfolio-value"))
            weights[ticker] = weight
            
    finally:
        driver.quit()
    
    return weights

def save_weights(weights, filename='portfolio_weights.json'):
    """Save weights to JSON file"""
    with open(filename, 'w') as f:
        json.dump(weights, f, indent=2, sort_keys=True)
    print(f"✅ Saved {len(weights)} portfolio weights to {filename}")

if __name__ == "__main__":
    weights = fetch_portfolio_weights_selenium()
    save_weights(weights)
