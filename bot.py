import slack
import os
import json
import threading
import glob
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

client.chat_postMessage(channel="#coffee_machine", text="JuraBot has restarted")
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
    
    # Check if the week record exsists, if not create one
    if os.path.exists("./"+team_id+"_week.json")==False:
        jfileWeek = open("./"+team_id+"_week.json", "x")
        recordWeek = {user_id:{"score" : 0, "user_name" : user_name}}
    elif os.stat("./"+team_id+"_week.json").st_size == 0:
        print("File empty, deleting and remaking...")
        os.remove("./"+team_id+"_week.json")
        jfile = open("./"+team_id+"_week.json", "x")
        record = {user_id:{"score" : 0, "user_name" : user_name}}
    else:
        # If json exists, load the json
        print("Opening week score json...")
        jfileWeek = open("./"+team_id+"_week.json")
        recordWeek = json.load(jfileWeek)

    # If new user, add user id to the dictionary
    print(f"Is user in record: {user_id in record}")
    if (user_id in record) == False:
        print("New user, updating record...")
        tempDict = {user_id:{"score":0, "user_name" : user_name}}
        record.update(tempDict)
    
    # For week record
    print(f"Is user in weekly record: {user_id in recordWeek}")
    if (user_id in recordWeek) == False:
        print("New user, updating weekly record...")
        tempDict = {user_id:{"score":0, "user_name" : user_name}}
        recordWeek.update(tempDict)

    print(f"Increasing {user_id}'s score by 1...")
    record[user_id]["score"] += 1
    recordWeek[user_id]["score"] += 1

    client.chat_postMessage(channel=channel_id, text=f'🧽➡️☕🤖 Jura Garbage Collection completed by {user_name} at {datetime.now().strftime("%H:%M")}')
    client.chat_postMessage(channel=channel_id, text=f"{user_name}'s cleaning 💦🧼 score is now: {record[user_id]['score']} overall, {recordWeek[user_id]['score']} for the week 🎉")


    print("Updating JSON files...")
    json.dump(record, open("./"+team_id+".json","w"))
    json.dump(recordWeek, open("./"+team_id+"_week.json","w"))

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
            client.chat_postMessage(channel=channel_id, text=f'You have {record[user_id]["score"]} points overall')
        else:
            client.chat_postMessage(channel=channel_id, text=f'You have no points. Maybe clean the coffee machine once?')
        
        sortRec = sorted(record, key=lambda x: (record[x]["score"]), reverse=True)
        client.chat_postMessage(channel=channel_id, text=f'🥉🥈🥇 Overall leaderboard (top 10 only) 🥇🥈🥉')
        c = 0
        for i in sortRec:
            if c > 9: break
            client.chat_postMessage(channel=channel_id, text=f'{record[i]["user_name"]}: {record[i]["score"]} points')
            c += 1
    else:
        client.chat_postMessage(channel=channel_id, text=f'No overall records yet...')

    if os.path.exists("./"+team_id+"_week.json"):
        jfileWeek = open("./"+team_id+"_week.json",)
        recordWeek = json.load(jfileWeek)
        if (user_id in recordWeek):
            client.chat_postMessage(channel=channel_id, text=f'You have {recordWeek[user_id]["score"]} points this week')

        sortRecWeek = sorted(recordWeek, key=lambda x: (record[x]["score"]), reverse=True)
        client.chat_postMessage(channel=channel_id, text=f'🏆 Weekly leaderboard 🏆')
        for i in sortRecWeek:
            client.chat_postMessage(channel=channel_id, text=f'{recordWeek[i]["user_name"]}: {recordWeek[i]["score"]} points')
    else:
        client.chat_postMessage(channel=channel_id, text=f'No week records yet...')

    return Response(), 200

# Alert people out of milk
@app.route("/milk", methods = ["POST"])
def milk():
    data = request.form
    print(data)
    channel_id = data.get("channel_id")

    client.chat_postMessage(channel=channel_id, text=f'<!channel> ☕🤖 JuraBot 🚫 OOM Error 🚨: Out Of Milk 🥛 🐮')
    return Response(), 200


def checkTime():
    # Checks the day once a day
    threading.Timer(86400, checkTime).start()

    day = datetime.today().weekday()

    teamInfo = client.team_info()
    teamDetails = teamInfo.get("team")
    team_id = teamDetails.get("id")

    # For testing:
    # day = 6

    # Day = 6 = Sunday: Post and reset weekly leaderboard on sunday
    if(day == 6):  # check if matches with the desired time
        jfileWeek = open("./"+team_id+"_week.json",)
        recordWeek = json.load(jfileWeek)
        sortRecWeek = sorted(recordWeek, key=lambda x: (recordWeek[x]["score"]), reverse=True)
        jfileWeek.close()
        
        client.chat_postMessage(channel="#coffee_machine", text=f"🗓️ It's Sunday 😴: Weekly leaderboard placement 🥇🥈🥉 ")
        for i in sortRecWeek:
            client.chat_postMessage(channel="#coffee_machine", text=f'{recordWeek[i]["user_name"]}: {recordWeek[i]["score"]} points')



        weekJsons = glob.glob("*_week.json")
        os.remove(weekJsons[0])
        client.chat_postMessage(channel="#coffee_machine", text=f"Leaderboard reset...💣💥")
        

checkTime()

if __name__ == "__main__":
    app.run(debug=True)
