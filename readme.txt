Orbital Bitcoin Mining Web App
=============================

This project simulates orbital BTC mining using a Flask-based web interface. It shows orbit and thermal visuals, radio link margins, and projected return on investment.

Setup Steps
-----------
1. **Install Python 3.10 or newer.** On Windows you can download it from the official Python website. Linux and macOS often have Python already installed.
2. **Install Git.** Visit [https://git-scm.com](https://git-scm.com) and follow the instructions for your operating system.
3. **Download the code.** Open a terminal or command prompt and run:

   ```
   git clone <repository-url>
   cd orbital_btc_mining
   ```

4. **Create a Python virtual environment.** This keeps dependencies isolated.

   ```
   python -m venv venv
   source venv/bin/activate      # On Windows use: venv\Scripts\activate
   ```

5. **Install required packages.**

   ```
   pip install -r requirements.txt
   ```

6. **Run the app.**

   ```
   python app.py
   ```

   Open your web browser to `http://127.0.0.1:5000`.

Usage
-----
Choose the orbit, launch vehicle and satellite class from the dropdowns. Adjust sliders for power, mission life, Bitcoin price growth and network hashrate growth. The page will update to show orbit and thermal charts, radio-frequency margins and a projected return on investment.

Notes
-----
- The MultiMW slider scales power from 1 to 60 MW and nears the theoretical limit at about 275 W/m² panel power density.
- Internet access is required for package installation.
