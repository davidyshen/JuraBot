import slack
import os
import json
import threading
import glob
import calendar
import sys
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

now = datetime.now()

if len(sys.argv) > 1:
    if sys.argv[1] == "d":  # d for deploy to coffee_machine channel
        client.chat_postMessage(channel="#coffee_machine", text=f'JuraBot is back online at {now.strftime("%d/%m/%Y, %H:%M:%S")}')
else:   # otherwise keep post messages to the testing channel
    client.chat_postMessage(channel="#jurabot-testing", text=f'JuraBot has restarted at {now.strftime("%d/%m/%Y, %H:%M:%S")}')

# Check if the hourly message has been sent yet
sent = False

BOT_ID = client.api_call("auth.test")["user_id"]

# Report machine was cleaned with /cleaned
@app.route("/cleaned", methods = ["POST"])
def cleaned():
    data = request.form
    # print(data)
    team_id = data.get("team_id")
    user_id = data.get("user_id")
    print("User_id = "+user_id)
    user_name = client.users_profile_get(user=user_id).get("profile").get("real_name")
    channel_id = data.get("channel_id")

    # Check if record json exists for the team, if not create one
    if os.path.exists("./"+team_id+".json")==False:
        jfile = open("./"+team_id+".json", "x")
        record = {user_id:{"score" : 0, "user_name" : user_name}}
    # Check if the record json is empty or not
    elif os.stat("./"+team_id+".json").st_size == 0:
        print("File empty, deleting and remaking...")
        os.remove("./"+team_id+".json")
        jfile = open("./"+team_id+".json", "x")
        record = {user_id:{"score" : 0, "user_name" : user_name}}
    else:
        # If json exists, load the json
        print("Opening score json...")
        jfile = open("./"+team_id+".json")
        record = json.load(jfile)
    
    # Check if the month record exsists, if not create one
    if os.path.exists("./"+team_id+"_month.json")==False:
        jfileMonth = open("./"+team_id+"_month.json", "x")
        recordMonth = {user_id:{"score" : 0, "user_name" : user_name}}
    elif os.stat("./"+team_id+"_month.json").st_size == 0:
        print("File empty, deleting and remaking...")
        os.remove("./"+team_id+"_month.json")
        jfile = open("./"+team_id+"_month.json", "x")
        record = {user_id:{"score" : 0, "user_name" : user_name}}
    else:
        # If json exists, load the json
        print("Opening month score json...")
        jfileMonth = open("./"+team_id+"_month.json")
        recordMonth = json.load(jfileMonth)

    # If new user, add user id to the dictionary
    print(f"Is user in record: {user_id in record}")
    if (user_id in record) == False:
        print("New user, updating record...")
        tempDict = {user_id:{"score":0, "user_name" : user_name}}
        record.update(tempDict)
    
    # For month record
    print(f"Is user in monthly record: {user_id in recordMonth}")
    if (user_id in recordMonth) == False:
        print("New user, updating monthly record...")
        tempDict = {user_id:{"score":0, "user_name" : user_name}}
        recordMonth.update(tempDict)

    print(f"Increasing {user_id}'s score by 1...")
    record[user_id]["score"] += 1
    recordMonth[user_id]["score"] += 1

    client.chat_postMessage(channel=channel_id, text=f'Jura Garbage Collection 🧽➡️☕🤖 completed by {user_name} at {datetime.now().strftime("%H:%M")}')
    client.chat_postMessage(channel=channel_id, text=f"{user_name}'s cleaning 💦🧼 score is now: {record[user_id]['score']} overall, {recordMonth[user_id]['score']} for the month 🎉")


    print("Updating JSON files...")
    json.dump(record, open("./"+team_id+".json","w"))
    json.dump(recordMonth, open("./"+team_id+"_month.json","w"))

    return Response(), 200


# Show leaderboard with /leaderboard
@app.route("/leaderboard", methods = ["POST"])
def leaderboard():
    data = request.form
    team_id = data.get("team_id")
    user_id = data.get("user_id")
    print("User_id = "+user_id)
    channel_id = data.get("channel_id")


    if os.path.exists("./"+team_id+".json"):
        jfile = open("./"+team_id+".json",)
        record = json.load(jfile)
        if (user_id in record):
            client.chat_postMessage(channel=channel_id, text=f'{record[user_id]["user_name"]}, you have {record[user_id]["score"]} points overall')
        else:
            client.chat_postMessage(channel=channel_id, text=f'<@{user_id}>, you have no points. Maybe clean the coffee machine once?')
        
        sortRec = sorted(record, key=lambda x: (record[x]["score"]), reverse=True)
        client.chat_postMessage(channel=channel_id, text=f'🥉🥈🥇 Overall leaderboard (top 10 only) 🥇🥈🥉')
        c = 0
        for i in sortRec:
            if c > 9: break
            client.chat_postMessage(channel=channel_id, text=f'{record[i]["user_name"]}: {record[i]["score"]} points')
            c += 1
    else:
        client.chat_postMessage(channel=channel_id, text=f'No overall records yet...')

    if os.path.exists("./"+team_id+"_month.json"):
        jfileMonth = open("./"+team_id+"_month.json",)
        recordMonth = json.load(jfileMonth)
        if (user_id in recordMonth):
            client.chat_postMessage(channel=channel_id, text=f'{recordMonth[user_id]["user_name"]}, you have {recordMonth[user_id]["score"]} points this month')

        sortRecMonth = sorted(recordMonth, key=lambda x: (record[x]["score"]), reverse=True)
        client.chat_postMessage(channel=channel_id, text=f'🏆 Monthly leaderboard 🏆')
        for i in sortRecMonth:
            client.chat_postMessage(channel=channel_id, text=f'{recordMonth[i]["user_name"]}: {recordMonth[i]["score"]} points')
    else:
        client.chat_postMessage(channel=channel_id, text=f'No month records yet...')

    return Response(), 200

# Alert people out of milk
@app.route("/milk", methods = ["POST"])
def milk():
    data = request.form
    print(data)
    channel_id = data.get("channel_id")

    client.chat_postMessage(channel=channel_id, text=f'<!channel> ☕🤖 JuraBot 🚫 OOM Error 🚨: Out Of Milk 🥛 🐮')
    return Response(), 200

# Alert people out of milk
@app.route("/milked", methods = ["POST"])
def milked():
    data = request.form
    print(data)
    channel_id = data.get("channel_id")

    client.chat_postMessage(channel=channel_id, text=f'Crisis averted: Milk replenished')
    return Response(), 200

@app.route("/r405", methods = ["GET"])
def r405():
    client.chat_postMessage(channel="C030BQPBNJC", text=f'<!channel> Your turn to service the coffee machine this week')
    return Response(), 200

@app.route("/r301", methods = ["GET"])
def r301():
    client.chat_postMessage(channel="C02NRD9R4UF", text=f'<!channel> Your turn to service the coffee machine this week')

    return Response(), 200

# @app.route("/r414", methods = ["GET"])
# def r414():
#     client.chat_postMessage(channel="C02L9BB8GDA", text=f'Test')

#     return Response(), 200

# @app.route("/r450", methods = ["GET"])
# def r450():
#     client.chat_postMessage(channel="C02L9BB8GDA", text=f'Test')

#     return Response(), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0')

