import boto3
import os 
import requests
import datetime 
import json

def refresh():
    query = "https://accounts.spotify.com/api/token"
    response = requests.post(query, 
                            data = {
                                "grant_type": "refresh_token", 
                                "refresh_token": "AQDbgv_5QSfXcHNtFNuGUhmetO9crJxzjlf6tl7ahssEWa269wXFYXi8h-5SnkV8ceZEro-DTyk2BiwmO99GdQ-l7oyjLqyvmLsom74bfZ4LZm0Jd-U8Yh4Rm1rwgdaCTds"
                            }, 
                            headers = {
                                "Authorization": "Basic MTI0OGU0ZTYxOGIwNDk1ZjkwNWFmY2EwNjMxMjQzZDY6YjQ5YjhmZDA2ZjNkNDg0NTg2MzYyMmQ0ZWE4ODMwNzE"
                            })
    return response.json()["access_token"]

def get_audio_features(id, header):
    r = requests.get("https://api.spotify.com/v1/audio-features/{id}".format(id=id), headers=header)
    data = r.json()
    collected_data = {}
    collected_data["danceability"] = str(data["danceability"])
    collected_data["energy"] = str(data["energy"])
    collected_data["loudness"] = str(data["loudness"])
    collected_data["speechiness"] = str(data["speechiness"])
    collected_data["acousticness"] = str(data["acousticness"])
    collected_data["instrumentalness"] = str(data["instrumentalness"])
    collected_data["liveness"] = str(data["liveness"])
    collected_data["valence"] = str(data["valence"])
    collected_data["tempo"] = str(data["tempo"])
    return(collected_data)

def get_spotify_info():
    access_token = refresh()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer {token}".format(token=access_token),
    }

    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    yesterday_unix_timestamp = int(yesterday.timestamp()) * 1000

    r = requests.get("https://api.spotify.com/v1/me/player/recently-played?limit=50&after={time}".format(time=yesterday_unix_timestamp), headers=headers)
    data = r.json()

    all_songs = []
    all_artists = []
    # in UTC
    played_at = []
    popularity = []
    audio_features = []

    total_danceability = 0
    total_energy = 0
    total_loudness = 0
    total_speechiness = 0
    total_acousticness = 0
    total_instrumentalness = 0
    total_liveness = 0
    total_valence = 0
    total_tempo = 0

    for song in data["items"]: 
        all_songs.append(song["track"]["name"])
        artists = []
        for elem in song["track"]["artists"]: 
            artists.append(elem["name"])
        all_artists.append(artists)
        played_at.append(song["played_at"][11:19])
        popularity.append(song["track"]["popularity"])
        audio_features_song = get_audio_features(song["track"]["id"], headers)
        audio_features.append(audio_features_song)

        total_danceability += float(audio_features_song["danceability"])
        total_energy += float(audio_features_song["energy"])
        total_loudness += float(audio_features_song["loudness"])
        total_speechiness += float(audio_features_song["speechiness"])
        total_acousticness += float(audio_features_song["acousticness"])
        total_instrumentalness += float(audio_features_song["instrumentalness"])
        total_liveness += float(audio_features_song["liveness"])
        total_valence += float(audio_features_song["valence"])
        total_tempo += float(audio_features_song["tempo"])
    
    averages = {}
    averages["danceability"] = str(total_danceability / len(data["items"]))
    averages["energy"] = str(total_energy / len(data["items"]))
    averages["loudness"] = str(total_loudness / len(data["items"]))
    averages["speechiness"] = str(total_speechiness / len(data["items"]))
    averages["acousticness"] = str(total_acousticness / len(data["items"]))
    averages["instrumentalness"] = str(total_instrumentalness / len(data["items"]))
    averages["liveness"] = str(total_liveness / len(data["items"]))
    averages["valence"] = str(total_valence / len(data["items"]))
    averages["tempo"] = str(total_tempo / len(data["items"]))
    return [all_songs, all_artists, played_at, popularity, audio_features, averages]

def lambda_handler(event: any, context: any):
    dynamodb = boto3.resource("dynamodb")
    table_name = os.environ["TABLE_NAME"]
    dates_table_name = os.environ["DATES_TABLE"]
    table = dynamodb.Table(table_name)
    dates_table = dynamodb.Table(dates_table_name)

    curr_day = str(datetime.datetime.now()).split(" ")[0]
    song_info = get_spotify_info()
    
    songs = song_info[0]
    artists = song_info[1]
    played_at = song_info[2]
    popularity = song_info[3]
    audio_features = song_info[4]
    averages = song_info[5]

    song_list = []
    if (len(songs) == len(artists) == len(played_at)):
        for i in range(len(songs)):
            curr_song = [songs[i], artists[i], played_at[i], popularity[i], audio_features[i]]
            song_list.append(curr_song)

    response = dates_table.get_item(
        Key={"all-dates": "all-dates"}
    )
    if "Item" in response:
        curr_dates = response["Item"]["dates"]
        curr_dates.append(curr_day)
        dates_table.put_item(
            Item={
                "all-dates": "all-dates", 
                "dates": curr_dates
            }
        )

    table.put_item(
        Item={
            "date": curr_day, 
            "played-songs": song_list, 
            "averages": averages
    })
    message = "successfully added!" 
    return {
        "message": message
    }

if __name__ == "__main__":
    os.environ["TABLE_NAME"] = "song-history"
    os.environ["DATES_TABLE"] = "dates"
    print(lambda_handler(None, None))