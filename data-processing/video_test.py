from googleapiclient.discovery import build

# Define your API key and initialize the YouTube API client
api_key = 'AIzaSyAszvr10v15JKi_nekkO-cLsBsMTxoBqrY'
youtube = build('youtube', 'v3', developerKey=api_key)

# Define the request to list videos from a specific channel
request = youtube.search().list(
    part='snippet',
    channelId='UC_x5XG1OV2P6uZZ5FSM9Ttw',  # Example channel ID
    maxResults=10
)

# Execute the request
response = request.execute()

# Print the response
for item in response['items']:
    print(f"Title: {item['snippet']['title']}")
    print(f"Description: {item['snippet']['description']}")
    print(f"Published at: {item['snippet']['publishedAt']}")
    print("----")

