from flask import Flask, render_template, request
import requests
import secrets
import json
import math
import sqlite3
import datetime

app = Flask(__name__)

sql_local = "fsrch.sqlite"
CACHE_FILENAME = "restaurants_cache.json"

SQL_INITIALIZED = False

def open_cache():
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close()

def execute_sql_read(query):
    connection = sqlite3.connect(sql_local)
    cursor = connection.cursor()
    result = cursor.execute(query).fetchall()
    connection.close()

    return result

def execute_sql_write(query):
    connection = sqlite3.connect(sql_local)
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    connection.close()

def execute_sql_write_with_params(query, params):
    connection = sqlite3.connect(sql_local)
    cursor = connection.cursor()
    cursor.execute(query, params)
    connection.commit()
    connection.close()


def db_fetch_all():
    connection = sqlite3.connect(sql_local)
    result = connection.cursor().fetchall()
    connection.close()
    return result

def drop_all_tables():

    query = "SELECT name FROM sqlite_master WHERE type='table'"
    result = execute_sql_read(query)

    for pair in result:
        if pair[0] == 'sqlite_sequence':
            continue
        dropQuery = "DROP TABLE IF EXISTS " + pair[0]
        execute_sql_write(dropQuery)

def init_sql():

    History_records = '''
        CREATE TABLE History_records (
            id INTEGER PRIMARY KEY,
            favore varchar(255),
            location varchar(255),
            numOfDisplay varchar(255),
            create_date timestamp
        );
    '''

    User = '''
        CREATE TABLE User (
            id INTEGER PRIMARY KEY,
            user_name varchar(255),
            email_address varchar(255),
            passwd varchar(255),
            create_date timestamp
        );
    '''

    query = "SELECT name FROM sqlite_master WHERE type='table'"
    result = execute_sql_read(query)
    all_tables = []
    for result_iter in result:
        all_tables.append(result_iter[0])

    table_list = ['History_records', 'User']

    for table_create in table_list:
        if table_create not in all_tables:
            execute_sql_write(eval(table_create))

@app.route('/')
def homepage():
    info = []
    return render_template("index.html", len=len(info), info=info)

@app.route('/search_items', methods=["POST"])
def search():

    user_favor = request.form["favor"]
    user_location = request.form["location"]
    user_display = request.form["numDisplay"]

    current_time = datetime.datetime.now()

    query = "SELECT COUNT(id) FROM History_records"
    result = execute_sql_read(query)
    search_counts = result[0][0]

    sqlite_insert_with_param = '''
        INSERT INTO History_records VALUES (?, ?, ?, ?, ?);
    '''

    params = (search_counts, user_favor, user_location, user_display, current_time)
    execute_sql_write_with_params(sqlite_insert_with_param, params)

    yelp_req = "https://api.yelp.com/v3/businesses/search"
    api_key=secrets.API_KEY
    headers = {'Authorization': 'Bearer %s' % api_key}

    params = {
        'term':user_favor,
        'location':user_location
    }

    stream_params = []
    for key, value in params.items():
        stream_params.append(key + "=" + value)
    cache_url = yelp_req + "&".join(stream_params)

    cache = open_cache()
    if cache_url in cache.keys():
        data = cache[cache_url]
        response = json.loads(data)
    else:
        req=requests.get(yelp_req, params=params, headers=headers)
        response = json.loads(req.text)
        cache[cache_url] = json.dumps(response)
        save_cache(cache)

    info = []
    for buss in response["businesses"][0:int(user_display)]:
        alias_list = []
        for alias in buss["categories"]:
            alias_list.append(alias["alias"])

        address = buss["location"]["address1"]

        buss_info = {
            "alias_name": " ".join(alias_list),
            "image_url": buss["image_url"],
            "name": buss["name"],
            "rating": buss["rating"],
            "phone": buss["phone"],
            "url": buss["url"],
            "id": buss["id"],
            "address": address,
            "is_closed": "closed" if buss["is_closed"] == "true" else "open"
        }

        info.append(buss_info)
        info_len = len(info)
        col = 3
        row = math.floor(info_len / 3)

    return render_template("search.html", row=row, col=col, len=info_len, info=info)

@app.route('/detail', methods=["POST"])
def detail():

    yelp_id = request.form["yelp_id"]
    yelp_req = "https://api.yelp.com/v3/businesses/" + yelp_id

    api_key=secrets.API_KEY
    headers = {'Authorization': 'Bearer %s' % api_key}
    
    cache = open_cache()
    if yelp_req in cache.keys():
        data = cache[yelp_req]
        response = json.loads(data)
    else:
        req=requests.get(yelp_req, headers=headers)
        response = json.loads(req.text)
        cache[yelp_req] = json.dumps(response)
        save_cache(cache)

    yelp_req = "https://api.yelp.com/v3/businesses/" + yelp_id + "/reviews"

    if yelp_req in cache.keys():
        data = cache[yelp_req]
        reviews_response = json.loads(data)
    else:
        req=requests.get(yelp_req, headers=headers)
        reviews_response = json.loads(req.text)
        cache[yelp_req] = json.dumps(reviews_response)
        save_cache(cache)

    response["reviews"] = reviews_response["reviews"]
    reviews = []

    for review_iter in reviews_response["reviews"]:
        review = {
            "user_name": review_iter["user"]["name"],
            "time_created": review_iter["time_created"],
            "user_rating": review_iter["rating"],
            "text": review_iter["text"]
        }
        reviews.append(review)

    info = {
        "name": response["name"],
        "image_url": response["image_url"],
        "transactions": response["transactions"],
        # display_address = " ".join(response["display_address"])
        "reviews": reviews
    }

    return render_template("reviews.html", len=len(reviews), info=info)

@app.route('/history', methods=["GET"])
def history():

    query = "SELECT * FROM History_records"
    result = execute_sql_read(query)

    info = []
    for result_iter in result:
        info_list = {
            "id": result_iter[0],
            "favor": result_iter[1],
            "location": result_iter[2],
            "numOfDisplay": result_iter[3],
            "create_date": result_iter[4],
        }
        info.append(info_list)

    return render_template("history.html", len=len(info), info=info)


if __name__ == "__main__":
    print("starting flask app ", app.name)

    if not SQL_INITIALIZED:
        drop_all_tables()
        init_sql()

    app.run(debug=True)