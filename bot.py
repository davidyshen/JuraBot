import slack
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, Response, request
from slackeventsapi import SlackEventAdapter

# Load slack tokens
env_path = Path(".")/".env"
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ["SIGNING_SECRET"],"/slack/events", app)

client = slack.WebClient(token=os.environ["SLACK_TOKEN"])

client.chat_postMessage(channel="#coffee", text="☕ JuraBot 🤖 has reconnected...")
BOT_ID = client.api_call("auth.test")["user_id"]

# @slack_event_adapter.on("message")
# def message(payload):
#     event = payload.get("event", {})
#     channel_id = event.get("channel")
#     user_id = event.get("user")
#     text = event.get("text")

#     if BOT_ID != user_id:
#         client.chat_postMessage(channel=channel_id, text=f"<@{user_id}>")

    # print(event)

# Report machine was cleaned with /cleaned
@app.route("/cleaned", methods = ["POST"])
def cleaned():
    data = request.form
    print(data)
    team_id = data.get("team_id")
    user_id = data.get("user_id")
    user_name = data.get("user_name")
    print("User_id = "+user_id)
    channel_id = data.get("channel_id")

    # Check if record json exists for the team, if not create one
    if os.path.exists("./"+team_id+".json")==False:
        open("./"+team_id+".json", "x")
        record = {user_id:{"score" : 0, "user_name" : user_name}}
    else:
        # If json exists, load the json
        jfile = open("./"+team_id+".json",)
        record = json.load(jfile)

    # If new user, add user id to the dictionary
    print(f"Is user in record: {user_id in record}")
    if (user_id in record) == False:
        print("New user, updating record...")
        tempDict = {user_id:{"score":0, "user_name" : user_name}}
        record.update(tempDict)

    print(f"Increasing {user_id}'s score by 1...")
    record[user_id]["score"] += 1

    client.chat_postMessage(channel=channel_id, text=f'☕🤖⬅️🧽🚿 by <@{user_id}> at {datetime.now().strftime("%H:%M")}')

    print("Updating JSON file...")
    json.dump(record, open("./"+team_id+".json", "w"))

    return Response(), 200


# Show leaderboard with /leaderboard
@app.route("/leaderboard", methods = ["POST"])
def leaderboard():
    data = request.form
    print(data)
    team_id = data.get("team_id")
    user_id = data.get("user_id")
    print("User_id = "+user_id)
    channel_id = data.get("channel_id")

    jfile = open("./"+team_id+".json",)
    record = json.load(jfile)


    client.chat_postMessage(channel=channel_id, text=f'{record[user_id]["user_name"]}')
    return Response(), 200


if __name__ == "__main__":
    app.run(debug=True)