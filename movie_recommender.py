import sys
import requests
import webbrowser
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTabWidget, QScrollArea,
                             QGridLayout, QFrame, QDialog, QFormLayout, QStatusBar, QMessageBox,
                             QComboBox, QTextEdit, QListWidget, QListWidgetItem)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
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
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
            }
            QLabel {
                color: #FFFFFF;
            }
            QLineEdit {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #FF0000;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
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
        self.normal_size = QSize(800, 800)  # Default size
        self.setFixedSize(self.normal_size)  # Start with normal size
        self.is_maximized = False
        
        # Add maximize button style to the existing style sheet
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
            }
            QLabel {
                color: #FFFFFF;
            }
            QListWidget {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
            }
            QScrollArea {
                background-color: #000000;
                border: none;
            }
            QTextEdit {
                background-color: #111111;
                color: #FFFFFF;
                border: none;
            }
            QFrame {
                background-color: #222222;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton {
                background-color: #FF0000;
                color: white;
                border-radius: 5px;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        
        self.content_type = content_type
        self.item_id = item_id
        self.tmdb_api_key = tmdb_api_key
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add maximize button in the title bar
        self.btn_maximize = QPushButton("⛶")  # Maximize symbol
        self.btn_maximize.setStyleSheet("""
            QPushButton {
                background: none;
                color: #FFFFFF;
                font-size: 16px;
                padding: 0px;
                min-width: 20px;
                max-width: 20px;
            }
            QPushButton:hover {
                color: #FF0000;
            }
        """)
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        
        # Create a title bar widget
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #222222; padding: 5px;")
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 0, 10, 0)
        
        self.title_label = QLabel("Details")
        self.title_label.setStyleSheet("font-size: 16px; color: #FF0000;")
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.btn_maximize)
        
        main_layout.addWidget(title_bar)
        
        # Scrollable content area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setStyleSheet("background-color: #000000;")
        self.content_layout = QVBoxLayout(self.content)
        self.scroll.setWidget(self.content)
        main_layout.addWidget(self.scroll)

        self.load_details()

    def toggle_maximize(self):
        if self.is_maximized:
            self.btn_maximize.setText("⛶")
            self.setFixedSize(self.normal_size)
            self.move(self.normal_position)
        else:
            self.btn_maximize.setText("🗗")
            self.normal_position = self.pos()
            self.setFixedSize(QApplication.desktop().availableGeometry().size())
            self.move(0, 0)
        self.is_maximized = not self.is_maximized

    def load_details(self):
        url = f"https://api.themoviedb.org/3/{self.content_type}/{self.item_id}"
        params = {
            "api_key": self.tmdb_api_key,
            "append_to_response": "combined_credits,images" if self.content_type == "person" 
                               else "credits,videos,reviews,recommendations,watch/providers"
        }
        self.worker = FetchWorker(url, params)
        self.worker.result.connect(self.display_details)
        self.worker.start()

    def display_details(self, data):
        if not data:
            self.content_layout.addWidget(QLabel("Failed to load details"))
            return

        if self.content_type == "person":
            self.display_person_details(data)
        else:
            self.display_media_details(data)

    def display_person_details(self, data):
        # Display person's name
        name = data.get("name", "Unknown")
        self.title_label.setText(f"Details - {name}")
        title_label = QLabel(f"<h1 style='color:#FF0000;'>{name}</h1>")
        self.content_layout.addWidget(title_label)

        # Main content frame
        main_frame = QFrame()
        main_frame.setStyleSheet("background-color: #222222; border-radius: 5px; padding: 10px;")
        main_layout = QHBoxLayout(main_frame)

        # Left column - Profile image
        profile_path = data.get("profile_path")
        if profile_path:
            try:
                img_data = requests.get(f"https://image.tmdb.org/t/p/original{profile_path}").content
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                pixmap = pixmap.scaled(300, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                poster_label = QLabel()
                poster_label.setPixmap(pixmap)
                main_layout.addWidget(poster_label)
            except Exception as e:
                print(f"Error loading profile image: {e}")
                main_layout.addWidget(QLabel("Image unavailable"))

        # Right column - Personal info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #333333; border-radius: 5px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)

        # Personal information
        also_known_as = data.get("also_known_as", [])
        if also_known_as and also_known_as[0] != name:
            info_layout.addWidget(QLabel(f"<b style='color:#FF0000;'>Real Name:</b> <span style='color:#FFFFFF;'>{also_known_as[0]}</span>"))

        birthday = data.get("birthday")
        if birthday:
            try:
                birth_date = datetime.strptime(birthday, "%Y-%m-%d")
                age = (datetime.now() - birth_date).days // 365
                info_layout.addWidget(QLabel(f"<b style='color:#FF0000;'>Age:</b> <span style='color:#FFFFFF;'>{age} years</span>"))
                info_layout.addWidget(QLabel(f"<b style='color:#FF0000;'>Birthday:</b> <span style='color:#FFFFFF;'>{birthday}</span>"))
            except:
                pass

        birthplace = data.get("place_of_birth")
        if birthplace:
            info_layout.addWidget(QLabel(f"<b style='color:#FF0000;'>Birthplace:</b> <span style='color:#FFFFFF;'>{birthplace}</span>"))

        # Biography
        biography = data.get("biography")
        if biography:
            bio_text = QTextEdit()
            bio_text.setPlainText(biography)
            bio_text.setReadOnly(True)
            bio_text.setStyleSheet("background-color: #111111; color: #FFFFFF; border: none;")
            info_layout.addWidget(QLabel("<b style='color:#FF0000;'>Biography:</b>"))
            info_layout.addWidget(bio_text)

        main_layout.addWidget(info_frame)
        self.content_layout.addWidget(main_frame)

        # Known for section
        known_for_frame = QFrame()
        known_for_frame.setStyleSheet("background-color: #222222; border-radius: 5px; padding: 10px; margin-top: 10px;")
        known_for_layout = QVBoxLayout(known_for_frame)
        known_for_layout.addWidget(QLabel("<h3 style='color:#FF0000;'>Known For</h3>"))

        credits = data.get("combined_credits", {})
        if credits:
            cast = sorted(credits.get("cast", []), 
                         key=lambda x: x.get("popularity", 0), 
                         reverse=True)[:5]  # Top 5 roles
            
            for role in cast:
                role_type = "Movie" if role.get("media_type") == "movie" else "TV Show"
                role_name = role.get("title") or role.get("name") or "Unknown"
                character = role.get("character") or "Unknown"
                
                role_frame = QFrame()
                role_frame.setStyleSheet("background-color: #333333; border-radius: 5px; padding: 5px;")
                role_layout = QHBoxLayout(role_frame)
                
                # Role poster
                poster_path = role.get("poster_path")
                if poster_path:
                    try:
                        img_data = requests.get(f"https://image.tmdb.org/t/p/w92{poster_path}").content
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_data)
                        poster_label = QLabel()
                        poster_label.setPixmap(pixmap)
                        role_layout.addWidget(poster_label)
                    except:
                        pass
                
                # Role info
                role_info = QLabel(f"<b>{role_name}</b> ({role_type})<br>as <i>{character}</i>")
                role_info.setStyleSheet("color: #FFFFFF;")
                role_info.setWordWrap(True)
                role_layout.addWidget(role_info)
                
                known_for_layout.addWidget(role_frame)

        self.content_layout.addWidget(known_for_frame)

        # Gallery section
        images = data.get("images", {}).get("profiles", [])
        if images:
            gallery_frame = QFrame()
            gallery_frame.setStyleSheet("background-color: #222222; border-radius: 5px; padding: 10px; margin-top: 10px;")
            gallery_layout = QVBoxLayout(gallery_frame)
            gallery_layout.addWidget(QLabel("<h3 style='color:#FF0000;'>Gallery</h3>"))

            images_layout = QHBoxLayout()
            for image in images[:5]:  # Show first 5 images
                try:
                    img_data = requests.get(f"https://image.tmdb.org/t/p/w185{image['file_path']}").content
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    poster_label = QLabel()
                    poster_label.setPixmap(pixmap)
                    images_layout.addWidget(poster_label)
                except:
                    pass
            
            gallery_layout.addLayout(images_layout)
            self.content_layout.addWidget(gallery_frame)

    def display_media_details(self, data):
        title = data.get("title") or data.get("name", "Unknown")
        self.title_label.setText(f"Details - {title}")
        title_label = QLabel(f"<h1 style='color:#FF0000;'>{title}</h1>")
        self.content_layout.addWidget(title_label)

        # Load and display poster image in color
        poster_path = data.get("poster_path") or data.get("profile_path")
        if poster_path:
            try:
                img_data = requests.get(f"https://image.tmdb.org/t/p/w200{poster_path}").content
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                pixmap = pixmap.scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                poster_label = QLabel()
                poster_label.setPixmap(pixmap)
                self.content_layout.addWidget(poster_label)
            except Exception as e:
                print(f"Error loading poster: {e}")
                self.content_layout.addWidget(QLabel("Poster unavailable"))

        overview = data.get("overview", "Not available")
        self.content_layout.addWidget(QLabel(f"<b style='color:#FF0000;'>Overview:</b> <span style='color:#FFFFFF;'>{overview}</span>"))

        if "credits" in data:
            cast = ", ".join([c["name"] for c in data["credits"].get("cast", [])[:5]]) or "Not available"
            self.content_layout.addWidget(QLabel(f"<b style='color:#FF0000;'>Cast:</b> <span style='color:#FFFFFF;'>{cast}</span>"))

        if "videos" in data and data["videos"].get("results"):
            trailer = next((v["key"] for v in data["videos"]["results"] if v["type"] == "Trailer" and v["site"] == "YouTube"), None)
            trailer_label = QLabel(f"<b style='color:#FF0000;'>Trailer:</b> <a href='https://www.youtube.com/watch?v={trailer}' style='color:#FFFFFF;'>Watch</a>" if trailer else "Not available")
            trailer_label.setOpenExternalLinks(True)
            self.content_layout.addWidget(trailer_label)

        if "watch/providers" in data and "US" in data["watch/providers"].get("results", {}):
            providers = data["watch/providers"]["results"]["US"].get("flatrate", [])
            provider_names = ", ".join([p["provider_name"] for p in providers]) or "Not available"
            self.content_layout.addWidget(QLabel(f"<b style='color:#FF0000;'>Watch on:</b> <span style='color:#FFFFFF;'>{provider_names}</span>"))

        if "reviews" in data and data["reviews"].get("results"):
            review = data["reviews"]["results"][0]["content"][:200] + "..." if data["reviews"]["results"] else "No reviews"
            self.content_layout.addWidget(QLabel(f"<b style='color:#FF0000;'>Review:</b> <span style='color:#FFFFFF;'>{review}</span>"))

        if "recommendations" in data and data["recommendations"].get("results"):
            recs = QListWidget()
            recs.setStyleSheet("color: #FFFFFF;")
            for rec in data["recommendations"]["results"][:5]:
                recs.addItem(rec.get("title") or rec.get("name"))
            self.content_layout.addWidget(QLabel("<b style='color:#FF0000;'>Recommendations:</b>"))
            self.content_layout.addWidget(recs)

# Main GUI class for the WatchX application
class TMDbGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WatchX")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #000000;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #FF0000;
                color: #FFFFFF;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
            QLineEdit {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
                border-radius: 15px;
                padding: 5px 15px;
            }
            QComboBox {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
                padding: 5px;
            }
            QTabWidget::pane {
                border: none;
                background: #000000;
            }
            QTabBar::tab {
                background: #222222;
                color: #FFFFFF;
                padding: 5px 15px;
                border-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #FF0000;
                color: #FFFFFF;
            }
            QScrollArea {
                background: #000000;
                border: none;
            }
            QStatusBar {
                background: #222222;
                color: #FFFFFF;
            }
        """)

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
        self.status_bar.showMessage("Welcome to WatchX!")

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
        header.setStyleSheet("background-color: #222222; padding: 10px;")
        header_layout = QHBoxLayout(header)

        logo_label = QLabel("WatchX")
        logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #FF0000;")
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
            btn.setStyleSheet("""
                QPushButton {
                    color: #FFFFFF;
                    background: none;
                    border: none;
                    font-size: 14px;
                }
                QPushButton:hover {
                    color: #FF0000;
                }
            """)
            btn.clicked.connect(lambda checked, c=category: self.switch_category(c))
            self.nav_buttons[category] = btn
            nav_layout.addWidget(btn)
        header_layout.addLayout(nav_layout)

        # Search bar with content type selector
        search_layout = QHBoxLayout()
        self.search_type = QComboBox()
        self.search_type.addItems(["Movies", "TV Shows", "People"])
        search_layout.addWidget(self.search_type)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search TMDb...")
        search_layout.addWidget(self.search_input)
        search_btn = QPushButton("🔍")
        search_btn.setStyleSheet("background: #FF0000; color: white; border-radius: 15px; padding: 5px;")
        search_btn.clicked.connect(self.search_content)
        search_layout.addWidget(search_btn)
        header_layout.addLayout(search_layout)

        # Login and Join buttons
        self.login_btn = QPushButton("Login")
        self.join_btn = QPushButton("Join TMDb")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: none;
                color: #FFFFFF;
                border: none;
            }
            QPushButton:hover {
                color: #FF0000;
            }
        """)
        self.join_btn.setStyleSheet("background: #FF0000; color: white; border-radius: 5px; padding: 5px 10px;")
        self.login_btn.clicked.connect(self.show_login_dialog)
        self.join_btn.clicked.connect(lambda: webbrowser.open("https://www.themoviedb.org/signup"))
        header_layout.addWidget(self.login_btn)
        header_layout.addWidget(self.join_btn)

        self.main_layout.addWidget(header)

    # Sets up the main content section with tabs and filter
    def setup_content_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        self.content_label = QLabel("Trending Movies")
        self.content_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FF0000;")
        content_layout.addWidget(self.content_label)

        # Filter combo box for content types
        self.filter_combo = QComboBox()
        content_layout.addWidget(self.filter_combo)

        # Tabs for Today and This Week views
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #000000;
            }
            QTabBar::tab {
                background: #222222;
                color: #FFFFFF;
                padding: 5px 15px;
                border-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #FF0000;
                color: #FFFFFF;
            }
        """)
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
        self.today_content.setStyleSheet("background-color: #000000;")
        self.today_grid = QGridLayout(self.today_content)
        self.today_scroll.setWidget(self.today_content)
        self.today_tab.setLayout(QVBoxLayout())
        self.today_tab.layout().addWidget(self.today_scroll)

        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_content = QWidget()
        self.week_content.setStyleSheet("background-color: #000000;")
        self.week_grid = QGridLayout(self.week_content)
        self.week_scroll.setWidget(self.week_content)
        self.week_tab.setLayout(QVBoxLayout())
        self.week_tab.layout().addWidget(self.week_scroll)

        self.main_layout.addWidget(content_widget)

    # Sets up footer with action buttons
    def setup_footer(self):
        footer = QFrame()
        footer.setStyleSheet("background-color: #222222; padding: 10px;")
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
            btn.setStyleSheet("""
                QPushButton {
                    background: #222222;
                    color: #FFFFFF;
                    border-radius: 15px;
                    padding: 5px 15px;
                    font-size: 14px;
                    border: 1px solid #FF0000;
                }
                QPushButton:hover {
                    background: #FF0000;
                }
            """)
            btn.clicked.connect(action)
            footer_layout.addWidget(btn)

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
                self.login_btn.setStyleSheet("""
                    QPushButton {
                        background: none;
                        color: #FF0000;
                        border: none;
                    }
                """)
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
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: none;
                color: #FFFFFF;
                border: none;
            }
            QPushButton:hover {
                color: #FF0000;
            }
        """)
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
            btn.setStyleSheet("""
                QPushButton {
                    color: #FFFFFF;
                    background: none;
                    border: none;
                    font-size: 14px;
                }
                QPushButton:hover {
                    color: #FF0000;
                }
            """ if btn_category != category else """
                QPushButton {
                    color: #FF0000;
                    background: none;
                    border: none;
                    font-size: 14px;
                }
            """)

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
            error_label.setStyleSheet("color: #FF0000;")
            target_grid.addWidget(error_label, 0, 0)
            return

        items = items[:8]  # Limit to 8 items for display
        for i, item in enumerate(items):
            item_widget = QWidget()
            item_widget.setStyleSheet("background-color: #222222; border-radius: 5px; padding: 10px;")
            item_layout = QVBoxLayout(item_widget)

            # Load and display image
            image_path = item.get("poster_path") or item.get("profile_path")
            if image_path:
                try:
                    img_data = requests.get(f"{self.tmdb_image_base_url}{image_path}").content
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    if self.current_content_type == "person":
                        pixmap = pixmap.scaled(150, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    else:
                        pixmap = pixmap.scaled(150, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    poster_label = QLabel()
                    poster_label.setPixmap(pixmap)
                except Exception as e:
                    print(f"Error loading image: {e}")
                    poster_label = QLabel("Image unavailable")
                    poster_label.setStyleSheet("color: #FFFFFF;")
                item_layout.addWidget(poster_label)

            # Content specific information
            if self.current_content_type == "person":
                # People display
                name = item.get("name", "Unknown")
                title_label = QLabel(name)
                title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
                title_label.setWordWrap(True)
                item_layout.addWidget(title_label)

                known_for = item.get("known_for", [])
                if known_for:
                    known_for_text = ", ".join([x.get("title") or x.get("name") or "Unknown" for x in known_for[:2]])
                    known_label = QLabel(known_for_text)
                    known_label.setStyleSheet("font-size: 12px; color: #AAAAAA;")
                    known_label.setWordWrap(True)
                    item_layout.addWidget(known_label)
            else:
                # Movie/TV show display
                rating = item.get("vote_average", 0) * 10 if "vote_average" in item else None
                if rating is not None:
                    rating_label = QLabel(f"{int(rating)}%")
                    rating_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF0000;")
                    item_layout.addWidget(rating_label)

                title = item.get("title") or item.get("name", "Unknown")
                title_label = QLabel(title)
                title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
                title_label.setWordWrap(True)
                item_layout.addWidget(title_label)

                date = item.get("release_date") or item.get("first_air_date", "N/A")
                date_label = QLabel(date)
                date_label.setStyleSheet("font-size: 12px; color: #AAAAAA;")
                item_layout.addWidget(date_label)

            # Common buttons
            item_id = item.get("id")
            detail_btn = QPushButton("Details")
            detail_btn.setStyleSheet("""
                QPushButton {
                    background: #FF0000;
                    color: white;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background: #CC0000;
                }
            """)
            detail_btn.clicked.connect(lambda checked, ct=self.current_content_type, id=item_id: DetailDialog(ct, id, self.tmdb_api_key, self).exec_())
            item_layout.addWidget(detail_btn)

            fav_btn = QPushButton("Favorite" if item_id not in self.favorites else "Unfavorite")
            fav_btn.setStyleSheet("""
                QPushButton {
                    background: #333333;
                    color: white;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background: #444444;
                }
            """)
            fav_btn.clicked.connect(lambda checked, id=item_id, t=title if self.current_content_type != "person" else name, b=fav_btn: self.toggle_favorite(id, t, b))
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
