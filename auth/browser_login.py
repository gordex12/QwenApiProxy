import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from core.config import set_qwen_token

def get_token_via_browser() -> str:
    """Open Chrome using Selenium to capture the QWEN token after manual login."""
    print("\n[Auth] No QWEN_TOKEN found in .env.")
    print("[Auth] Opening the browser to login into the Qwen platform...")
    print("[Auth] Please log in to your account. The system will wait to automatically capture the token.")
    
    options = Options()
    # Disable automation flags to prevent Google login block
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # To disguise Selenium further, we add a common User-Agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    token = None
    
    try:
        driver = webdriver.Chrome(options=options)
        
        # Script to remove webdriver from navigator
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        
        driver.get("https://chat.qwen.ai/auth")
        
        print("\n[Auth] Waiting for authentication and token generation...")
        
        while True:
            # Get all cookies from the current session
            cookies = driver.get_cookies()
            for cookie in cookies:
                # The site saves the access token in the 'token' cookie or in localStorage/sessionStorage.
                # Assuming the instruction: "a cookie named token"
                if cookie['name'] == 'token':
                    token = cookie['value']
                    break
            
            if token:
                print("\n[Auth] Token successfully captured!")
                break
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n[Auth] Login interrupted by the user.")
    except Exception as e:
        print(f"\n[Auth] An error occurred while capturing the token: {e}")
    finally:
        if driver:
            driver.quit()
            
    if token:
        set_qwen_token(token)
        print("[Auth] Token automatically saved to the .env file.\n")
        
    return token
