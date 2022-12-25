""""""
# 載入 json 標準函式庫，處理回傳的資料格式
import datetime
import flask
import json
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import timeTB

from flask import request
from datetime import datetime

from timeTB.model import get_db

# 載入 LINE Message API 相關函式庫
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage

ACCESS_TOKEN = 'q0uht3Iq6VLsTPzj1dEIVGkhw+ouU2F2Z7w7fYFFF8izIXsGE3tfXIl6uOVbGqng2GskRVn+WpcIqgaFtPPxiJHiXixOpSbXPXFZd9GKSIix/wPl7PXCwi5MLF0/qaR0GmKcbair7JdmA3al+0JjhAdB04t89/1O/w1cDnyilFU='
SECRET = '455cc7a29bdef41b5aac17129f556731'

@timeTB.app.route("/", methods=['POST'])
def handle_msg():
    data_str = request.get_data(as_text=True)
    data_dict = json.loads(data_str)

    try:
        line_bot_api = LineBotApi(ACCESS_TOKEN)              # 確認 token 是否正確
        handler = WebhookHandler(SECRET)                     # 確認 secret 是否正確
        signature = request.headers['X-Line-Signature']      # 加入回傳的 headers
        handler.handle(data_str, signature)                  # 綁定訊息回傳的相關資訊
    except Exception as exp:
        print("Error in establishing connection")
        print(exp)

    try:
        events = data_dict.get('events')
    except:
        return 'OK'

    for event in events: 
        reply = handle_event(event)
        line_bot_api.reply_message(
            event['replyToken'],
            reply
        )  # 回傳訊息

    return 'OK' # 驗證 Webhook 使用，不能省略


def handle_event(event):
    userID = event.get('source', {})
    userID = userID.get("userId", None)
    if userID:
        try:
            if event['message']['type'] == 'text':
                msg = event['message']['text'].split('.')  # 取得 LINE 收到的文字訊息
                if msg[0] == "IN":
                    reply = info_input(userID, msg[1].split(','))
                    return TextSendMessage(reply)
                elif msg[0] == "OUT":
                    return gantt_chart(userID, msg)
                else:
                    return TextSendMessage("指令須以'IN.'或是'OUT.'開頭")
        except Exception as exp:
            return TextSendMessage(f'發生錯誤: {exp}')                   


def info_input(userID, dirty_msg):
    """
    Takes in a list of str.
    Store the task indicated by the list of string into db.
    Returns a string.
    """
    msg, err = input_process_in(dirty_msg)
    if err:
        return err

    try:
        print(msg)
        conn = get_db()
        conn.execute(
            "INSERT INTO users(userid,startdate,enddate,title,location,memo) "
            "VALUES(?,?,?,?,?,?) ",
            (userID, msg[0], msg[1], msg[2], msg[3], msg[4])
        )
        return "已成功將行程加入資料庫。欲瀏覽目前行程，請輸入「YYYY-MM-DD YYYY-MM-DD」以選取顯示範圍。"
    except:
        return "資料庫發生錯誤，請稍後再嘗試。"


def input_process_in(dirty_msg):
    """
    Makes sure the input format is correct
    Return a list of string formatted as
    [start_date, end_date, title, location (optional), memo (optional)]
    start_date and end_date are in format 'YYYY-MM-DD HH:mm'
    """
    if len(dirty_msg)<2 or len(dirty_msg)>4:
        return None, "輸入項目數量錯誤"

    date_time = dirty_msg[0].strip()
    err = "日期格式錯誤"
    try:
        if len(date_time) == 10: # 1 date
            start_date = f"{date_time} 00:00"
            end_date = f"{date_time} 23:59"
        elif len(date_time) == 21: # 2 dates
            start_date = f"{date_time[:10]} 00:00"
            end_date = f"{date_time[11:]} 23:59"
        elif len(date_time) == 22: # 1 date and HH:MM-HH:MM
            start_date = date_time[:16]
            end_date = f"{date_time[:10]} {date_time[17:]}"
        else:
            return None, err
    except:
        return None, err
    
    ans = [start_date, end_date, dirty_msg[1].strip()]
    if len(dirty_msg)>=3: # has location
        ans.append(dirty_msg[2].strip())
    else:
        ans.append("")
    if len(dirty_msg)==4: # has memo
        ans.append(dirty_msg[3].strip())
    else:
        ans.append("")

    return ans, None


def gantt_chart(userID, msg):
    """
    Return either TextSendMessage() or ImageSendMessage()
    """
    try:
        conn = get_db()
    except:
            return "資料庫發生錯誤，請稍後再嘗試。"
    events = pd.DataFrame(columns=['Task', 'Start', 'Finish', 'Location', 'Memo'])

    if msg[1].strip() == "Date":
        dates, err = input_process_out(msg[2].split())
        if err:
            return TextSendMessage(err)
        cur = conn.execute(
            "SELECT * "
            "FROM users "
            "WHERE userid = ? AND NOT startdate > ? AND NOT enddate < ? ",
            (userID, dates[1], dates[0], )
        )
        query = cur.fetchall()
        for q in query:
            if q['startdate'] < dates[0]:
                q['startdate'] = dates[0]
            if q['enddate'] > dates[1]:
                q['enddate'] = dates[1]
            events = events.append({
                'Task': title,
                'Start': q['startdate'],
                'Finish': q['enddate'],
                'Location': q.get('location', ""),
                'Memo': q.get('memo', "")
            }, ignore_index=True)

    elif msg[1].strip() == "Task":
        tasks = msg[2].split(',')
        for title in tasks:
            title = title.strip()
            cur = conn.execute(
                "SELECT * "
                "FROM users "
                "WHERE userid = ? AND title = ? ",
                (userID, title, )
            )

            query = cur.fetchall()
            for q in query:
                events = events.append({
                    'Task': title,
                    'Start': q['startdate'],
                    'Finish': q['enddate'],
                    'Location': q.get('location', ""),
                    'Memo': q.get('memo', "")
                }, ignore_index=True)

    else:
        return TextSendMessage(f"無法辨識{msg[1]}，'OUT.'之後請輸入'Task'或是'Date'")

    fig = px.timeline(events, x_start="Start", x_end="Finish", y="Task", color="Task", hover_data=['Location', 'Memo'])
    fig.update_yaxes(autorange="reversed")
    filepath = f"var/{userID}_{datetime.now()}.jpeg"
    fig.write_image(filepath) #TODO is this okay as an url????
    ImageSendMessage(original_content_url=filepath, preview_image_url=filepath)

def input_process_out(dirty_msg):
    dirty_msg = dirty_msg.strip()
    err = "日期格式錯誤"
    if len(dirty_msg) != 21:
        return None, err

    dates = dirty_msg.split(' ')
    if len(dates) != 2:
        return None, err
    if len(dates[0]) != 10 or len(dates[1]) != 10:
        return None, err
    
    try:
        ans = []
        for date_str in dates:
            print(f"|{date_str}|")
            ans.append(datetime.strptime(date_str, '%Y-%m-%d'))
    except:
        return None, err
    
    delta = ans[1] - ans[0]
    if delta.days > 7 or delta.days < 0:
        return None, "本功能僅支援範圍為1至7天的行事曆"
    
    return ans, None


if __name__ == "__main__":
    timeTB.app.run(debug=True)
