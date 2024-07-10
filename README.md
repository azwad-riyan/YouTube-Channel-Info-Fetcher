
# YouTube Channel Info Fetcher



## Introduction

One day, while visiting one of my favorite YouTube channels, I wondered how many hours of video the channel had uploaded. I realized there wasn't any online tool that provided this information, including the total video duration for a channel. Most tools only showed the number of videos and other statistics, but not the total video length. So, I decided to create a tool that could fetch and display this information. I hope you find it useful!


## Features
- Fetch total uploaded video length for a YouTube channel in their lifetime
- Display channel statistics(Subs count, view count etc.)
- List all playlists and number of videos in each
- Export the fetched information to a PDF


## Requirements

To run this tool, you need to have Python installed along with the following libraries:

- The API key
- PyQt5
- google-api-python-client
- isodate
- reportlab
- PyPDF2
You can install these libraries using pip:
```bash
  pip install PyQt5 google-api-python-client isodate reportlab PyPDF2
```

## Executable File
For those who don't have Python installed, an executable file is provided in the releases. This allows you to run the tool without needing to install Python or any additional libraries. So simple. 
# Usage/Examples
## Step-by-Step Instructions
### 1. Clone the repository:
```bash
git clone https://github.com/yourusername/YouTubeChannelInfoFetcher.git
cd YouTubeChannelInfoFetcher

```
### 2. Run the tool
```bash
python main.py
```
And that's all, enjoy!


## Getting a Google API Key
To use this tool, you'll need a Google API key. Follow these steps to get your API key:

### 1. Go to the [Google Cloud Console.](https://console.cloud.google.com/)
### 2. Create a new project or select an existing one.
### 3. Go to the [API & Services dashboard.](https://console.cloud.google.com/apis/dashboard)
### 4. Click on Enable APIs and Services.
### 5. Search for YouTube Data API v3 and enable it.
### 6. Go to [Credentials](https://console.cloud.google.com/apis/credentials) and click on Create Credentials.
### 7. Select API Key and copy the generated key.

For a more detailed guide, check the [official documentation.](https://developers.google.com/youtube/documentation)
# Using the Tool
## Start the application:
1. Enter your Google API key and click on Submit API Key.
2. Enter the YouTube channel URL and click on Get Info.
3. The tool will fetch and display the channel information, including the total video length and playlist details.
4. You can export this information to a PDF by clicking on Export as PDF in your perfered directory.
## Screenshots

![SS (1)](https://github.com/azwad-riyan/YouTube-Channel-Info-Fetcher/assets/112563850/2b081ae0-ef39-441d-a440-072ffd8c3700)

![SS (2)](https://github.com/azwad-riyan/YouTube-Channel-Info-Fetcher/assets/112563850/758cf17e-7d40-4fc6-a485-6c435e05e782)
![SS (3)](https://github.com/azwad-riyan/YouTube-Channel-Info-Fetcher/assets/112563850/9f1bb25f-f1bb-4ae0-8841-326804d31f5c)

## Contributing

Feel free to fork this repository, make your changes, and submit a pull request. Your contributions are welcome!

## Notes
- Ensure that your API key has the necessary permissions to access the YouTube Data API.
- The tool may take some time to fetch data for channels with a large number of videos. Please be patient.
