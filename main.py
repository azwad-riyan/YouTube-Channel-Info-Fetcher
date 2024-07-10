import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QProgressBar, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QFormLayout, QStackedWidget, QCheckBox, QTableWidgetItem, QTableWidget
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QPropertyAnimation, QRect
import googleapiclient.discovery
from datetime import timedelta, datetime
import isodate
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from PyPDF2 import PdfReader, PdfWriter
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class FetchDataThread(QThread):
    data_fetched = pyqtSignal(tuple)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int)  # Added int for elapsed time

    def __init__(self, api_key, channel_url):
        QThread.__init__(self)
        self.api_key = api_key
        self.channel_url = channel_url
        self.start_time = None

    def run(self):
        try:
            self.start_time = datetime.now()
            youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=self.api_key)
            channel_id = self.get_channel_id(youtube, self.channel_url)
            if not channel_id:
                raise ValueError("Please enter a valid YouTube channel URL.")

            channel_info = self.fetch_channel_info(youtube, channel_id)
            playlists = self.fetch_playlists(youtube, channel_id)
            total_playlists = len(playlists)
            total_videos = sum(len(self.fetch_videos(youtube, playlist['id'])) for playlist in playlists)
            total_requests = total_playlists + total_videos
            request_count = 0

            playlist_details = {}
            total_duration = timedelta()

            for index, playlist in enumerate(playlists):
                playlist_id = playlist['id']
                playlist_title = playlist['snippet']['title']
                videos = self.fetch_videos(youtube, playlist_id)
                playlist_video_count = len(videos)
                playlist_details[playlist_title] = playlist_video_count
                playlist_duration = self.calculate_total_duration(youtube, videos)
                total_duration += playlist_duration

                # Emit progress signal for each playlist fetched
                request_count += 1
                elapsed_time = (datetime.now() - self.start_time).total_seconds()
                self.progress_updated.emit(int(request_count / total_requests * 100), int(elapsed_time))

                # Emit progress signals for each video fetched within the playlist
                video_request_count = 0
                for video in videos:
                    video_request_count += 1
                    elapsed_time = (datetime.now() - self.start_time).total_seconds()
                    self.progress_updated.emit(int(((request_count - 1) + (video_request_count / len(videos))) / total_requests * 100), int(elapsed_time))

            # Ensure progress bar hits 100% at the end
            self.progress_updated.emit(100, int((datetime.now() - self.start_time).total_seconds()))

            self.data_fetched.emit((channel_info, total_duration, total_playlists, total_videos, playlist_details))

        except Exception as e:
            self.error_occurred.emit(str(e))

    def get_channel_id(self, youtube, channel_url):
        channel_id = None
        if 'channel/' in channel_url:
            channel_id = channel_url.split('channel/')[1]
        elif 'user/' in channel_url:
            username = channel_url.split('user/')[1]
            response = youtube.channels().list(forUsername=username, part="id").execute()
            if 'items' in response and len(response['items']) > 0:
                channel_id = response['items'][0]['id']
        elif '@' in channel_url:
            handle = channel_url.split('@')[1]
            response = youtube.search().list(q=handle, part="snippet", type="channel").execute()
            if 'items' in response and len(response['items']) > 0:
                channel_id = response['items'][0]['snippet']['channelId']
        return channel_id

    def fetch_channel_info(self, youtube, channel_id):
        response = youtube.channels().list(id=channel_id, part="snippet,statistics").execute()
        if 'items' in response and len(response['items']) > 0:
            channel_snippet = response['items'][0]['snippet']
            channel_statistics = response['items'][0]['statistics']
            channel_title = channel_snippet.get('title', '')
            channel_author = channel_snippet.get('title', '')  # Assuming author name is the same as channel title for simplicity
            total_subscribers = channel_statistics.get('subscriberCount', 'Unknown')
            total_views = channel_statistics.get('viewCount', 'Unknown')
            channel_created = channel_snippet.get('publishedAt', '').split('T')[0]  # Get the date portion
            return {
                'title': channel_title,
                'author': channel_author,
                'subscribers': total_subscribers,
                'views': total_views,
                'created': channel_created
            }
        return {}

    def fetch_playlists(self, youtube, channel_id):
        playlists = []
        request = youtube.playlists().list(channelId=channel_id, part="id,snippet", maxResults=50)
        while request:
            response = request.execute()
            playlists.extend(response.get('items', []))
            request = youtube.playlists().list_next(request, response)
        return playlists

    def fetch_videos(self, youtube, playlist_id):
        videos = []
        request = youtube.playlistItems().list(playlistId=playlist_id, part="contentDetails", maxResults=50)
        while request:
            response = request.execute()
            videos.extend(response.get('items', []))
            request = youtube.playlistItems().list_next(request, response)
        return videos

    def calculate_total_duration(self, youtube, videos):
        total_duration = timedelta()
        for video in videos:
            video_id = video['contentDetails']['videoId']
            video_response = youtube.videos().list(id=video_id, part="contentDetails").execute()
            if 'items' in video_response and len(video_response['items']) > 0:
                video_duration = video_response['items'][0]['contentDetails']['duration']
                total_duration += isodate.parse_duration(video_duration)
        return total_duration

class YouTubeFetcherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_key_file = resource_path("api_key.txt")
        self.api_key = self.load_api_key()
        self.initUI()
        self.total_duration = timedelta()
        self.num_playlists = 0
        self.total_videos = 0
        self.playlist_details = {}
        self.channel_info = {}
        self.progress_bar_timer = QTimer(self)

        if self.api_key:
            self.transition_to_main_page()

    def initUI(self):
        self.setWindowTitle("YouTube Channel Info Fetcher by Riyan")
        self.setGeometry(100, 100, 800, 600)

        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)

        self.initAPIKeyPage()
        self.initMainPage()

    def initAPIKeyPage(self):
        api_key_widget = QWidget()
        layout = QVBoxLayout(api_key_widget)

        form_layout = QFormLayout()
        self.api_key_input = QLineEdit()
        form_layout.addRow("YouTube API Key:", self.api_key_input)
        layout.addLayout(form_layout)

        self.save_api_key_checkbox = QCheckBox("Save API Key")
        layout.addWidget(self.save_api_key_checkbox)

        self.api_key_button = QPushButton("Submit API Key")
        self.api_key_button.clicked.connect(self.on_api_key_submit)
        layout.addWidget(self.api_key_button)

        self.stacked_widget.addWidget(api_key_widget)

    def initMainPage(self):
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        form_layout = QFormLayout()
        self.channel_url_input = QLineEdit()
        form_layout.addRow("YouTube Channel URL: (Ex-https://www.youtube.com/@name)", self.channel_url_input)
        layout.addLayout(form_layout)

        self.fetch_button = QPushButton("Get Info")
        self.fetch_button.clicked.connect(self.on_fetch_click)
        layout.addWidget(self.fetch_button)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.result_text = QLabel("")
        layout.addWidget(self.result_text)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Playlist Title", "Number of Videos"])
        layout.addWidget(self.table)

        self.export_button = QPushButton("Export as PDF")
        self.export_button.clicked.connect(self.on_export_click)
        layout.addWidget(self.export_button)

        self.progress_bar_label = QLabel("")
        layout.addWidget(self.progress_bar_label)

        self.estimated_time_label = QLabel("")
        layout.addWidget(self.estimated_time_label)

        self.stacked_widget.addWidget(main_widget)

    def on_api_key_submit(self):
        self.api_key = self.api_key_input.text()
        if not self.api_key:
            QMessageBox.warning(self, "Warning", "Please enter a valid API key.")
            return
        if self.save_api_key_checkbox.isChecked():
            self.save_api_key(self.api_key)
        self.transition_to_main_page()

    def transition_to_main_page(self):
        main_page_index = self.stacked_widget.indexOf(self.stacked_widget.widget(1))
        self.stacked_widget.setCurrentIndex(main_page_index)
        animation = QPropertyAnimation(self.stacked_widget, b"geometry")
        animation.setDuration(1000)
        animation.setStartValue(QRect(0, 0, 800, 600))
        animation.setEndValue(QRect(100, 100, 800, 600))
        animation.start()

    def on_fetch_click(self):
        channel_url = self.channel_url_input.text()
        self.progress_bar.setValue(0)
        self.progress_bar_label.setText("Collecting data from YouTube...")

        self.thread = FetchDataThread(self.api_key, channel_url)
        self.thread.data_fetched.connect(self.on_data_fetched)
        self.thread.error_occurred.connect(self.on_error)
        self.thread.progress_updated.connect(self.on_progress_updated)
        self.thread.start()

        self.progress_bar_timer.timeout.connect(self.update_progress_bar_text)
        self.progress_bar_timer.start(5000)  # Update text every 5 seconds

    def on_progress_updated(self, value, elapsed_time):
        self.progress_bar.setValue(value)
        estimated_total_time = int((elapsed_time / value) * 100) if value > 0 else 0
        remaining_time = estimated_total_time - elapsed_time
        self.estimated_time_label.setText(f"Estimated time remaining: {remaining_time} seconds")

    def on_data_fetched(self, result):
        self.progress_bar_timer.stop()
        self.channel_info, self.total_duration, self.num_playlists, self.total_videos, self.playlist_details = result
        self.result_text.setText(f"Channel: {self.channel_info.get('title', '')}\nAuthor: {self.channel_info.get('author', '')}\nSubscribers: {self.channel_info.get('subscribers', 'Unknown')}\nTotal Views: {self.channel_info.get('views', 'Unknown')}\nChannel Created: {self.channel_info.get('created', '')}\nTotal Video Length: {self.format_duration(self.total_duration)}\nNumber of Playlists: {self.num_playlists}\nTotal Number of Videos: {self.total_videos}")

        self.table.setRowCount(0)
        for title, count in self.playlist_details.items():
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(title))
            self.table.setItem(row_position, 1, QTableWidgetItem(str(count)))

        self.progress_bar_label.setText("Data fetching complete!")
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Done!")

    def on_error(self, error_message):
        self.progress_bar_timer.stop()
        QMessageBox.critical(self, "Error", error_message)
        self.progress_bar_label.setText("Error fetching data.")

    def format_duration(self, duration):
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}:{minutes:02}:{seconds:02}"

    def update_progress_bar_text(self):
        if self.progress_bar.value() < 100:
            if self.progress_bar.value() < 80:
                self.progress_bar.setFormat("Getting data from YouTube takes time, please be patient...")
            else:
                self.progress_bar.setFormat("We are almost there, please wait a bit more...")

    def on_export_click(self):
        if not self.playlist_details:
            QMessageBox.warning(self, "Warning", "No data to export. Please fetch the data first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if not file_path:
            return

        self.export_data(file_path, self.channel_info, self.total_duration, self.num_playlists, self.total_videos, self.playlist_details)

    def export_data(self, file_path, channel_info, total_duration, num_playlists, total_videos, playlist_details):
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []

        # Title
        styles = getSampleStyleSheet()
        title = Paragraph("YouTube Channel Summary", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))

        # Channel Info
        channel_info_data = [
            ["Channel", channel_info.get('title', '')],
            ["Author", channel_info.get('author', '')],
            ["Subscribers", channel_info.get('subscribers', 'Unknown')],
            ["Total Views", channel_info.get('views', 'Unknown')],
            ["Channel Created on", channel_info.get('created', '')]
        ]
        channel_info_table = Table(channel_info_data, colWidths=[200, 200])
        channel_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(channel_info_table)
        elements.append(Spacer(1, 24))

        # Summary Table
        summary_data = [
            ["Total Video Length", self.format_duration(total_duration)],
            ["Number of Playlists", num_playlists],
            ["Total Number of Videos", total_videos]
        ]
        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 24))

        # Playlist Details Table
        playlist_data = [["Playlist Title", "Number of Videos"]]
        for title, count in playlist_details.items():
            playlist_data.append([title, count])
        playlist_table = Table(playlist_data, colWidths=[300, 100])
        playlist_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(playlist_table)

        # Build the main document
        doc.build(elements)

        QMessageBox.information(self, "Success", "Data exported successfully!")

    def save_api_key(self, api_key):
        with open(self.api_key_file, 'w') as file:
            file.write(api_key)

    def load_api_key(self):
        if os.path.exists(self.api_key_file):
            with open(self.api_key_file, 'r') as file:
                return file.read().strip()
        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeFetcherApp()
    window.show()
    sys.exit(app.exec_())
