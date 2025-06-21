Here’s a step-by-step guide to run your trading bot on an old Windows PC:

---

### 1. **Install Python**

- Download Python 3.x from [python.org](https://www.python.org/downloads/windows/).
- During installation, **check the box** that says “Add Python to PATH”.

---

### 2. **Install Git (optional, for code sync)**

- Download from [git-scm.com](https://git-scm.com/download/win).
- This lets you clone your repo and pull updates easily.

---

### 3. **Clone or Copy Your Project**

- If using Git:
    ```sh
    git clone https://github.com/yourusername/your-repo.git
    ```
- Or copy your project folder to the PC.

---

### 4. **Create and Activate a Virtual Environment**

Open Command Prompt (`cmd`) and run:
```sh
cd path\to\your\project
python -m venv venv
venv\Scripts\activate
```

---

### 5. **Install Dependencies**

```sh
pip install -r requirements.txt
```
Or, if you don’t have a `requirements.txt`, install manually:
```sh
pip install oandapyV20 pandas numpy lightgbm joblib
```

---

### 6. **Set Up Secrets**

- **For environment variables:**  
  Open Command Prompt and run:
  ```sh
  set EMAIL_APP_PASSWORD=your_16_character_app_password
  ```
  Or, create a `.env` file in your project folder with:
  ```
  EMAIL_APP_PASSWORD=your_16_character_app_password
  ```

- **Edit your config file** (live_trader_config.py) with your OANDA and email details.

---

### 7. **Test the Script**

Run your script manually to make sure it works:
```sh
python run_live_trade.py
```
Check for errors and fix any missing dependencies or config issues.

---

### 8. **Schedule the Script (Windows Task Scheduler)**

1. Open **Task Scheduler** (search in Start menu).
2. Click **Create Basic Task**.
3. Name it (e.g., “TradingBot”).
4. **Trigger:** Choose “Daily” (you’ll set the interval next).
5. **Action:** Choose “Start a program”.
6. **Program/script:**  
   - Browse to your Python executable (e.g., `C:\Users\YourName\yourproject\venv\Scripts\python.exe`)
7. **Add arguments:**  
   - run_live_trade.py
8. **Start in:**  
   - The full path to your project folder (e.g., `C:\Users\YourName\yourproject`)
9. **Finish** the wizard.
10. In the Task Scheduler Library, **right-click your task → Properties → Triggers tab → Edit**.  
    - Set “Repeat task every” to **15 minutes** for a duration of 24 hours.

---

### 9. **Log Output**

- In your script, print output to a log file (as you do on Mac).
- You can set up Task Scheduler to redirect output, or add this to your script:
    ```python
    import sys
    sys.stdout = open('tradebot.log', 'a')
    sys.stderr = sys.stdout
    ```

---

### 10. **Notifications**

- Email notifications will work the same way as on Mac, as long as your environment variable is set.

---

**Summary:**  
- Use Python, virtualenv, and Task Scheduler (not cron) on Windows.
- Set environment variables via `.env` or `set` command.
- Use Task Scheduler to run every 15 minutes.
- Logs and notifications work as before.

Let me know if you want a sample `.bat` file or Task Scheduler XML for automation!