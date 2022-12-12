# Quickstart - Python example app

This is an example showing how to implement a chatbot using LanyingIM API and OpenAI API.
This project runs with python 3.7

## Setup

1. If you don’t have Python installed, [install it from here](https://www.python.org/downloads/)

2. Clone this repository

3. Navigate into the project directory

   ```bash
   $ cd lanying-connector
   ```

4. Create a new virtual environment

   ```bash
   $ python3 -m venv venv
   $ . venv/bin/activate
   ```

5. Install the requirements

   ```bash
   $ pip install -r requirements.txt
   ```

6. Make a copy of the example environment variables file

   ```bash
   $ cp .env.example .env
   ```

7. In the newly created `.env` file, set LANYING_USER_ID to the user ID of the LanyingIM chatbot, set LANYING_ADMIN_TOKEN to the LanyingIM administrator Token, and set LANYING_CONNECTOR_SERVICE to the selected service. The current possible value is openai.

8. If LANYING_CONNECTOR_SERVICE is set to openai, modify the OpenAI configuration file configs/openai.json , the `openai_api_key` field must be set to your [OPENAI API key](https://beta.openai.com/account/api-keys).

9. Run the app

   ```bash
   $ flask run
   ```

You should now be able to access the app at [http://localhost:5000](http://localhost:5000)! 
