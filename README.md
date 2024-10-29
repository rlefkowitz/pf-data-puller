# Pro Football Data Puller!
Welcome! This is the project page for a data scraper on https://pro-football-reference.com to provide data for a Senior Capstone Project at Haverford College focused on the influence of childhood economic circumstances on athletic performance of professional athletes.

## Usage
NOTE: Currently, you will need a [Zyte](https://www.zyte.com/) api key to get things rolling (place it in a file at the root called `.env` in the same format as `.env.example`). This is for proxying requests so we don't have to abide by those painfully slow rate limits (10req/min).
You will also need a Zyte CA, or certificate. Make sure you call it `zyte-ca.crt` and place it at the root of the project. After following the below instructions for creating a virtual environment, run `python combine_certs.py`. This should produce a file called `combined-ca-bundle.crt`.

Using this project is straightforward. Simply open the terminal, navigate to a desirable location (optional), and clone the repository.

### If you have a Unix-based OS
Once you've cloned, you can run `make run`! This will set up requirements with a virtual environment `venv` and execute the script inside of that virtual environment.

If you prefer conda, I'm sure you already know what to do. The requirements are in `requirements.txt`. Make sure you're using `python3.12`.
However, `make run` does depend on using a venv, so you'll need to enter the environment, ensure you've installed the requirements, and then call `python scraper.py`.

### Windows Users
This project will work just fine. If you're comfortable with it, using `python3.12` set up a virtualenv (preferrably) or a conda environment. Then, `source` into the workspace, run `pip install -r requirements.txt`. Once that's all done, you're home free. Run `python scraper.py`!
