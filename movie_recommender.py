import sys
import requests
import webbrowser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTabWidget, QScrollArea,
                             QGridLayout, QFrame, QDialog, QFormLayout, QStatusBar, QMessageBox,
                             QComboBox, QTextEdit, QListWidget, QListWidgetItem)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
import os

# Worker thread for asynchronous API requests to avoid blocking the GUI
class FetchWorker(QThread):
    result = pyqtSignal(dict)  # Signal to emit API response

    def __init__(self, url, params=None, headers=None):
        super().__init__()
        self.url = url
        self.params = params or {}
        self.headers = headers or {}

    # Executes the API request in a separate thread
    def run(self):
        try:
            response = requests.get(self.url, params=self.params, headers=self.headers, timeout=10)
            response.raise_for_status()  # Raises exception for HTTP errors
            self.result.emit(response.json())  # Emit successful response
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            self.result.emit({})  # Emit empty dict on failure

# Dialog for simulated user login
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setFixedSize(300, 150)
        layout = QFormLayout(self)
        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)  # Hide password input
        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)
        login_btn = QPushButton("Login", self)
        login_btn.clicked.connect(self.accept)  # Close dialog on login
        layout.addWidget(login_btn)

# Dialog to display detailed information about a movie, TV show, or person
class DetailDialog(QDialog):
    def __init__(self, content_type, item_id, tmdb_api_key, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Details")
        self.setFixedSize(600, 600)
        self.content_type = content_type  # Type: movie, tv, or person
        self.item_id = item_id  # TMDb ID of the item
        self.tmdb_api_key = tmdb_api_key
        layout = QVBoxLayout(self)

        # Scrollable area for detailed content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

        self.load_details()  # Start loading details

    # Initiates the API call to fetch item details
    def load_details(self):
        url = f"https://api.themoviedb.org/3/{self.content_type}/{self.item_id}"
        params = {"api_key": self.tmdb_api_key, "append_to_response": "credits,videos,reviews,recommendations,watch/providers"}
        self.worker = FetchWorker(url, params)
        self.worker.result.connect(self.display_details)
        self.worker.start()

    # Displays detailed information fetched from TMDb
    def display_details(self, data):
        if not data:
            self.content_layout.addWidget(QLabel("Failed to load details"))
            return

        title = data.get("title") or data.get("name", "Unknown")
        self.setWindowTitle(f"Details - {title}")
        self.content_layout.addWidget(QLabel(f"<b>{title}</b>"))

        # Load and display poster image in color
        poster_path = data.get("poster_path") or data.get("profile_path")
        if poster_path:
            try:
                img_data = requests.get(f"https://image.tmdb.org/t/p/w200{poster_path}").content
                image = Image.open(BytesIO(img_data)).convert("RGB")  # Ensure RGB for color
                image = image.resize((150, 225))
                qimage = QImage(image.tobytes(), image.width, image.height, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)  # Load as color image
                poster_label = QLabel()
                poster_label.setPixmap(pixmap)
                self.content_layout.addWidget(poster_label)
            except Exception as e:
                print(f"Error loading poster: {e}")
                self.content_layout.addWidget(QLabel("Poster unavailable"))

        # Add overview, cast, trailer, providers, reviews, and recommendations
        overview = data.get("overview", "Not available")
        self.content_layout.addWidget(QLabel(f"<b>Overview:</b> {overview}"))

        if "credits" in data:
            cast = ", ".join([c["name"] for c in data["credits"].get("cast", [])[:5]]) or "Not available"
            self.content_layout.addWidget(QLabel(f"<b>Cast:</b> {cast}"))

        if "videos" in data and data["videos"].get("results"):
            trailer = next((v["key"] for v in data["videos"]["results"] if v["type"] == "Trailer" and v["site"] == "YouTube"), None)
            trailer_label = QLabel(f"<b>Trailer:</b> <a href='https://www.youtube.com/watch?v={trailer}'>Watch</a>" if trailer else "Not available")
            trailer_label.setOpenExternalLinks(True)  # Make link clickable
            self.content_layout.addWidget(trailer_label)

        if "watch/providers" in data and "US" in data["watch/providers"].get("results", {}):
            providers = data["watch/providers"]["results"]["US"].get("flatrate", [])
            provider_names = ", ".join([p["provider_name"] for p in providers]) or "Not available"
            self.content_layout.addWidget(QLabel(f"<b>Watch on:</b> {provider_names}"))

        if "reviews" in data and data["reviews"].get("results"):
            review = data["reviews"]["results"][0]["content"][:200] + "..." if data["reviews"]["results"] else "No reviews"
            self.content_layout.addWidget(QLabel(f"<b>Review:</b> {review}"))

        if "recommendations" in data and data["recommendations"].get("results"):
            recs = QListWidget()
            for rec in data["recommendations"]["results"][:5]:
                recs.addItem(rec.get("title") or rec.get("name"))
            self.content_layout.addWidget(QLabel("<b>Recommendations:</b>"))
            self.content_layout.addWidget(recs)

# Main GUI class for the TMDb Explorer application
class TMDbGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TMDb Explorer")
        self.setGeometry(100, 100, 1200, 800)

        # Load API keys from .env file
        load_dotenv()
        self.tmdb_api_key = os.getenv("TMDB_API_KEY")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")

        if not all([self.tmdb_api_key, self.youtube_api_key, self.rapidapi_key]):
            print("Error: Missing API keys in .env file")
            sys.exit(1)

        # Initialize variables and caches
        self.tmdb_image_base_url = "https://image.tmdb.org/t/p/w200"
        self.trailer_cache = {}
        self.streaming_cache = {}
        self.logged_in = False
        self.username = None
        self.favorites = []  # Local list for favorited items

        # Set up central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Add status bar for user feedback
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Welcome to TMDb Explorer!")

        # Initialize UI components
        self.setup_header()
        self.setup_content_section()
        self.setup_footer()

        # Load initial content
        self.current_content_type = "movie"
        self.load_content("movie", "trending", "day")

    # Sets up the header with logo, navigation, search, and login/join buttons
    def setup_header(self):
        header = QFrame()
        header_layout = QHBoxLayout(header)

        logo_label = QLabel("TMDb Explorer")
        logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #01d277;")
        header_layout.addWidget(logo_label)

        # Navigation buttons for categories
        nav_layout = QHBoxLayout()
        self.nav_options = {
            "Movies": [("Trending", "trending"), ("Popular", "popular"), ("Now Playing", "now_playing"), ("Top Rated", "top_rated")],
            "TV Shows": [("Trending", "trending"), ("Popular", "popular"), ("Airing Today", "airing_today"), ("Top Rated", "top_rated")],
            "People": [("Popular", "popular")]
        }
        self.nav_buttons = {}
        for category, options in self.nav_options.items():
            btn = QPushButton(category)
            btn.setStyleSheet("color: white; background: none; border: none; font-size: 14px;")
            btn.clicked.connect(lambda checked, c=category: self.switch_category(c))
            self.nav_buttons[category] = btn
            nav_layout.addWidget(btn)
        header_layout.addLayout(nav_layout)

        # Search bar with content type selector
        search_layout = QHBoxLayout()
        self.search_type = QComboBox()
        self.search_type.addItems(["Movies", "TV Shows", "People"])
        self.search_type.setStyleSheet("padding: 5px;")
        search_layout.addWidget(self.search_type)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search TMDb...")
        self.search_input.setStyleSheet("padding: 5px; border-radius: 15px; border: 1px solid #ccc;")
        search_layout.addWidget(self.search_input)
        search_btn = QPushButton("🔍")
        search_btn.setStyleSheet("background: #01d277; color: white; border-radius: 15px; padding: 5px;")
        search_btn.clicked.connect(self.search_content)
        search_layout.addWidget(search_btn)
        header_layout.addLayout(search_layout)

        # Login and Join buttons
        self.login_btn = QPushButton("Login")
        self.join_btn = QPushButton("Join TMDb")
        self.login_btn.setStyleSheet("background: none; color: white; border: none;")
        self.join_btn.setStyleSheet("background: #01d277; color: white; border-radius: 5px; padding: 5px 10px;")
        self.login_btn.clicked.connect(self.show_login_dialog)
        self.join_btn.clicked.connect(lambda: webbrowser.open("https://www.themoviedb.org/signup"))
        header_layout.addWidget(self.login_btn)
        header_layout.addWidget(self.join_btn)

        header.setStyleSheet("background-color: #032541; padding: 10px;")
        self.main_layout.addWidget(header)

    # Sets up the main content section with tabs and filter
    def setup_content_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        self.content_label = QLabel("Trending Movies")
        self.content_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        content_layout.addWidget(self.content_label)

        # Filter combo box for content types
        self.filter_combo = QComboBox()
        self.filter_combo.setStyleSheet("padding: 5px;")
        content_layout.addWidget(self.filter_combo)

        # Tabs for Today and This Week views
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabBar::tab { background: #e0e0e0; padding: 5px 15px; border-radius: 5px; } "
                           "QTabBar::tab:selected { background: #01d277; color: white; }")
        self.today_tab = QWidget()
        self.week_tab = QWidget()
        tabs.addTab(self.today_tab, "Today")
        tabs.addTab(self.week_tab, "This Week")
        tabs.currentChanged.connect(self.on_tab_changed)
        content_layout.addWidget(tabs)

        # Scrollable areas for content grids
        self.today_scroll = QScrollArea()
        self.today_scroll.setWidgetResizable(True)
        self.today_content = QWidget()
        self.today_grid = QGridLayout(self.today_content)
        self.today_scroll.setWidget(self.today_content)
        self.today_tab.setLayout(QVBoxLayout())
        self.today_tab.layout().addWidget(self.today_scroll)

        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_content = QWidget()
        self.week_grid = QGridLayout(self.week_content)
        self.week_scroll.setWidget(self.week_content)
        self.week_tab.setLayout(QVBoxLayout())
        self.week_tab.layout().addWidget(self.week_scroll)

        self.main_layout.addWidget(content_widget)

    # Sets up footer with action buttons
    def setup_footer(self):
        footer = QFrame()
        footer_layout = QHBoxLayout(footer)

        footer_items = {
            "Latest Trailers": self.show_latest_trailers,
            "Popular": lambda: self.load_content(self.current_content_type, "popular", "day"),
            "Streaming": lambda: self.load_content(self.current_content_type, "trending", "day"),
            "On TV": lambda: self.load_content("tv", "airing_today", "day"),
            "For Rent": lambda: self.load_content(self.current_content_type, "trending", "day"),
            "In Theatres": lambda: self.load_content("movie", "now_playing", "day")
        }
        for text, action in footer_items.items():
            btn = QPushButton(text)
            btn.setStyleSheet("background: #e0e0e0; border-radius: 15px; padding: 5px 15px; font-size: 14px;")
            btn.clicked.connect(action)
            footer_layout.addWidget(btn)

        footer.setStyleSheet("background-color: #032541; padding: 10px;")
        self.main_layout.addWidget(footer)

    # Shows the login dialog and handles simulated login
    def show_login_dialog(self):
        dialog = LoginDialog(self)
        if dialog.exec_():
            username = dialog.username_input.text().strip()
            password = dialog.password_input.text().strip()
            if username and password:
                self.logged_in = True
                self.username = username
                self.login_btn.setText(f"Welcome, {username}")
                self.login_btn.setStyleSheet("background: none; color: #01d277; border: none;")
                self.login_btn.clicked.disconnect()
                self.login_btn.clicked.connect(self.logout)
                self.status_bar.showMessage(f"Logged in as {username}")
            else:
                QMessageBox.warning(self, "Login Failed", "Please enter both username and password.")

    # Logs out the user and resets the login button
    def logout(self):
        self.logged_in = False
        self.username = None
        self.login_btn.setText("Login")
        self.login_btn.setStyleSheet("background: none; color: white; border: none;")
        self.login_btn.clicked.disconnect()
        self.login_btn.clicked.connect(self.show_login_dialog)
        self.status_bar.showMessage("Logged out")

    # Switches the content category and updates filter options
    def switch_category(self, category):
        self.current_content_type = "movie" if category == "Movies" else "tv" if category == "TV Shows" else "person"
        self.content_label.setText(f"{category}")
        self.filter_combo.clear()
        for opt in self.nav_options[category]:
            self.filter_combo.addItem(opt[0], opt[1])
        self.filter_combo.currentTextChanged.connect(lambda text: self.load_content(self.current_content_type, self.filter_combo.currentData(), "day"))
        self.load_content(self.current_content_type, self.nav_options[category][0][1], "day")
        for btn_category, btn in self.nav_buttons.items():
            btn.setStyleSheet("color: white; background: none; border: none; font-size: 14px;" if btn_category != category else "color: #01d277; background: none; border: none; font-size: 14px;")

    # Searches TMDb based on user input and selected type
    def search_content(self):
        query = self.search_input.text().strip()
        if not query:
            self.status_bar.showMessage("Please enter a search query")
            return
        content_type = "movie" if self.search_type.currentText() == "Movies" else "tv" if self.search_type.currentText() == "TV Shows" else "person"
        self.status_bar.showMessage(f"Searching {self.search_type.currentText()} for '{query}'...")
        url = f"https://api.themoviedb.org/3/search/{content_type}"
        params = {"api_key": self.tmdb_api_key, "query": query}
        self.worker = FetchWorker(url, params)
        self.worker.result.connect(self.display_content)
        self.worker.start()

    # Handles tab switching between Today and This Week
    def on_tab_changed(self, index):
        self.load_content(self.current_content_type, self.filter_combo.currentData(), "day" if index == 0 else "week")

    # Loads content based on type, filter, and time window
    def load_content(self, content_type, filter_type, time_window):
        self.current_content_type = content_type
        self.current_filter = filter_type
        self.status_bar.showMessage(f"Loading {content_type} - {filter_type} for {time_window}...")
        self.clear_layout(self.today_grid)
        self.clear_layout(self.week_grid)
        url = f"https://api.themoviedb.org/3/{filter_type}/{content_type}/{time_window}" if filter_type == "trending" else f"https://api.themoviedb.org/3/{content_type}/{filter_type}"
        params = {"api_key": self.tmdb_api_key}
        self.worker = FetchWorker(url, params)
        self.worker.result.connect(self.display_content)
        self.worker.start()

    # Loads and displays the latest item for trailer viewing
    def show_latest_trailers(self):
        self.status_bar.showMessage(f"Loading latest trailers for {self.current_content_type}...")
        url = f"https://api.themoviedb.org/3/{self.current_content_type}/latest"
        params = {"api_key": self.tmdb_api_key}
        self.worker = FetchWorker(url, params)
        self.worker.result.connect(lambda data: self.display_content({"results": [data] if data else []}))
        self.worker.start()

    # Clears a layout by removing and deleting its widgets
    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    # Displays fetched content in the grid
    def display_content(self, data):
        target_grid = self.today_grid if "day" in self.worker.url or "trending" not in self.worker.url else self.week_grid
        self.clear_layout(target_grid)
        items = data.get("results", [])
        self.status_bar.showMessage("Content loaded successfully" if items else "Failed to load content")

        if not items:
            error_label = QLabel("No results found or failed to load.")
            error_label.setStyleSheet("color: red;")
            target_grid.addWidget(error_label, 0, 0)
            return

        items = items[:8]  # Limit to 8 items for display
        for i, item in enumerate(items):
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)

            # Load and display poster image in color
            poster_path = item.get("poster_path") or item.get("profile_path")
            if poster_path:
                try:
                    img_data = requests.get(f"{self.tmdb_image_base_url}{poster_path}").content
                    image = Image.open(BytesIO(img_data)).convert("RGB")  # Ensure RGB for color
                    image = image.resize((150, 225))
                    qimage = QImage(image.tobytes(), image.width, image.height, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimage)  # Load as color image
                    poster_label = QLabel()
                    poster_label.setPixmap(pixmap)
                except Exception as e:
                    print(f"Error loading poster: {e}")
                    poster_label = QLabel("Image unavailable")
                item_layout.addWidget(poster_label)

            # Add rating, title, date, and interaction buttons
            rating = item.get("vote_average", 0) * 10 if "vote_average" in item else None
            if rating is not None:
                rating_label = QLabel(f"{int(rating)}%")
                rating_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #01d277;")
                item_layout.addWidget(rating_label)

            title = item.get("title") or item.get("name", "Unknown")
            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            title_label.setWordWrap(True)
            item_layout.addWidget(title_label)

            date = item.get("release_date") or item.get("first_air_date", "N/A")
            date_label = QLabel(date)
            date_label.setStyleSheet("font-size: 12px; color: #666;")
            item_layout.addWidget(date_label)

            item_id = item.get("id")
            detail_btn = QPushButton("Details")
            detail_btn.setStyleSheet("background: #01d277; color: white; border-radius: 5px;")
            detail_btn.clicked.connect(lambda checked, ct=self.current_content_type, id=item_id: DetailDialog(ct, id, self.tmdb_api_key, self).exec_())
            item_layout.addWidget(detail_btn)

            fav_btn = QPushButton("Favorite" if item_id not in self.favorites else "Unfavorite")
            fav_btn.setStyleSheet("background: #e0e0e0; border-radius: 5px;")
            fav_btn.clicked.connect(lambda checked, id=item_id, t=title, b=fav_btn: self.toggle_favorite(id, t, b))
            item_layout.addWidget(fav_btn)

            row = i // 4
            col = i % 4
            target_grid.addWidget(item_widget, row, col)

    # Toggles an item as a favorite and updates UI
    def toggle_favorite(self, item_id, title, button):
        if item_id in self.favorites:
            self.favorites.remove(item_id)
            button.setText("Favorite")
            self.status_bar.showMessage(f"Removed {title} from favorites")
        else:
            self.favorites.append(item_id)
            button.setText("Unfavorite")
            self.status_bar.showMessage(f"Added {title} to favorites")

# Main entry point to run the application
def main():
    app = QApplication(sys.argv)
    try:
        window = TMDbGUI()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
