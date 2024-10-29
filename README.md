
# 🏈 Pro Football Data Puller!

Welcome! This is the project page for a data scraper targeting [Pro Football Reference](https://pro-football-reference.com) 🏆.

## 🚀 Quick Start

> **Note**: You’ll need a [Zyte](https://www.zyte.com/) API key 🔑 to get things rolling! Place it in a `.env` file at the root of this project, following the format in `.env.example`. This helps us bypass slow rate limits (10 req/min). Also, be sure to have a Zyte certificate file `zyte-ca.crt` at the root. Run `python combine_certs.py` afterward to create `combined-ca-bundle.crt`.

### 🛠 Setup Steps

1. **Clone the repository**: Open your terminal, navigate to your desired location, and clone the repo.
2. **Install Requirements**:

#### 🐧 For Unix-based OS
- Run `make run` to set up a virtual environment (`venv`) and install requirements. The script will execute inside the virtual environment.
- If you’re using Conda, use `requirements.txt` and ensure you’re running `python3.12`.
  - ⚠️ Note: `make run` depends on using `venv`. Enter the environment, install requirements, and then run `python scraper.py`.

#### 🖥️ For Windows Users
- Set up a virtual environment (or Conda) with `python3.12`. Activate it, then run `pip install -r requirements.txt`.
- After setup, simply run `python scraper.py` to start scraping! 🎉

## 🤝 Contributing
Feel free to fork the repo and make pull requests for any improvements.

Happy scraping! 🚀
