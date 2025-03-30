import sys
import requests
import webbrowser
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTabWidget, QScrollArea,
                             QGridLayout, QFrame, QDialog, QFormLayout, QStatusBar, QMessageBox,
                             QComboBox, QTextEdit, QListWidget, QListWidgetItem)
from PyQt5.QtGui import QPixmap, QImage, QFont
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
        self.setFixedSize(350, 180)
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #FF0000;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        layout = QFormLayout(self)
        layout.setVerticalSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Set font for the dialog
        font = QFont()
        font.setFamily("Arial")
        self.setFont(font)
        
        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)  # Hide password input
        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)
        
        # Button container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        login_btn = QPushButton("Login", self)
        login_btn.clicked.connect(self.accept)  # Close dialog on login
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("background-color: #444444;")
        
        button_layout.addWidget(login_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow(button_container)

# Dialog to display detailed information about a movie, TV show, or person
class DetailDialog(QDialog):
    def __init__(self, content_type, item_id, tmdb_api_key, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Details")
        self.normal_size = QSize(900, 900)  # Larger default size
        self.setFixedSize(self.normal_size)  # Start with normal size
        self.is_maximized = False
        
        # Enhanced style sheet with better typography
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            QLabel {
                color: #FFFFFF;
            }
            QListWidget {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
                font-size: 14px;
            }
            QScrollArea {
                background-color: #121212;
                border: none;
            }
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: none;
                font-size: 14px;
                padding: 10px;
            }
            QFrame {
                background-color: #222222;
                border-radius: 8px;
                padding: 15px;
            }
            QPushButton {
                background-color: #FF0000;
                color: white;
                border-radius: 5px;
                padding: 8px;
                min-width: 100px;
                font-size: 14px;
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
        
        # Custom title bar with maximize button
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #222222; padding: 10px;")
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(15, 5, 15, 5)
        
        self.title_label = QLabel("Details")
        self.title_label.setStyleSheet("font-size: 18px; color: #FF0000; font-weight: bold;")
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        
        self.btn_maximize = QPushButton("⛶")  # Maximize symbol
        self.btn_maximize.setStyleSheet("""
            QPushButton {
                background: none;
                color: #FFFFFF;
                font-size: 18px;
                padding: 0px;
                min-width: 24px;
                max-width: 24px;
            }
            QPushButton:hover {
                color: #FF0000;
            }
        """)
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        title_bar_layout.addWidget(self.btn_maximize)
        
        main_layout.addWidget(title_bar)
        
        # Scrollable content area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setStyleSheet("background-color: #121212;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        self.scroll.setWidget(self.content)
        main_layout.addWidget(self.scroll)

        # Set default font for better readability
        font = QFont()
        font.setFamily("Arial")
        self.setFont(font)
        
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
            error_label = QLabel("Failed to load details")
            error_label.setStyleSheet("color: #FF0000; font-size: 16px;")
            self.content_layout.addWidget(error_label)
            return

        if self.content_type == "person":
            self.display_person_details(data)
        else:
            self.display_media_details(data)

    def display_person_details(self, data):
        # Display person's name
        name = data.get("name", "Unknown")
        self.title_label.setText(f"Details - {name}")
        
        # Main content frame
        main_frame = QFrame()
        main_frame.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 15px;")
        main_layout = QHBoxLayout(main_frame)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Left column - Profile image (larger size)
        profile_path = data.get("profile_path")
        if profile_path:
            try:
                img_data = requests.get(f"https://image.tmdb.org/t/p/original{profile_path}").content
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                pixmap = pixmap.scaled(350, 525, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                poster_label = QLabel()
                poster_label.setPixmap(pixmap)
                poster_label.setAlignment(Qt.AlignCenter)
                main_layout.addWidget(poster_label)
            except Exception as e:
                print(f"Error loading profile image: {e}")
                error_label = QLabel("Image unavailable")
                error_label.setStyleSheet("color: #FFFFFF; font-size: 14px;")
                main_layout.addWidget(error_label)

        # Right column - Personal info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #333333; border-radius: 8px; padding: 15px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(15)

        # Name with larger font
        name_label = QLabel(f"<h1 style='color:#FF0000; margin-bottom: 10px;'>{name}</h1>")
        info_layout.addWidget(name_label)

        # Personal information with better formatting
        also_known_as = data.get("also_known_as", [])
        if also_known_as and also_known_as[0] != name:
            info_layout.addWidget(QLabel(
                f"<p style='color:#FFFFFF; font-size: 15px; margin: 5px 0;'>"
                f"<b style='color:#FF0000;'>Real Name:</b> {also_known_as[0]}</p>"
            ))

        birthday = data.get("birthday")
        if birthday:
            try:
                birth_date = datetime.strptime(birthday, "%Y-%m-%d")
                age = (datetime.now() - birth_date).days // 365
                info_layout.addWidget(QLabel(
                    f"<p style='color:#FFFFFF; font-size: 15px; margin: 5px 0;'>"
                    f"<b style='color:#FF0000;'>Age:</b> {age} years</p>"
                ))
                info_layout.addWidget(QLabel(
                    f"<p style='color:#FFFFFF; font-size: 15px; margin: 5px 0;'>"
                    f"<b style='color:#FF0000;'>Birthday:</b> {birthday}</p>"
                ))
            except:
                pass

        birthplace = data.get("place_of_birth")
        if birthplace:
            info_layout.addWidget(QLabel(
                f"<p style='color:#FFFFFF; font-size: 15px; margin: 5px 0;'>"
                f"<b style='color:#FF0000;'>Birthplace:</b> {birthplace}</p>"
            ))

        # Biography with better formatting
        biography = data.get("biography")
        if biography:
            bio_text = QTextEdit()
            bio_text.setPlainText(biography)
            bio_text.setReadOnly(True)
            bio_text.setStyleSheet("""
                QTextEdit {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    border: none;
                    font-size: 14px;
                    padding: 10px;
                    border-radius: 5px;
                }
            """)
            info_layout.addWidget(QLabel("<h3 style='color:#FF0000; margin-bottom: 5px;'>Biography</h3>"))
            info_layout.addWidget(bio_text)

        main_layout.addWidget(info_frame)
        self.content_layout.addWidget(main_frame)

        # Known for section with improved layout
        known_for_frame = QFrame()
        known_for_frame.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 15px; margin-top: 10px;")
        known_for_layout = QVBoxLayout(known_for_frame)
        known_for_layout.setContentsMargins(10, 10, 10, 10)
        known_for_layout.setSpacing(15)
        
        known_for_layout.addWidget(QLabel("<h2 style='color:#FF0000; margin-bottom: 10px;'>Known For</h2>"))

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
                role_frame.setStyleSheet("background-color: #333333; border-radius: 8px; padding: 10px;")
                role_layout = QHBoxLayout(role_frame)
                role_layout.setContentsMargins(10, 10, 10, 10)
                role_layout.setSpacing(15)
                
                # Role poster (larger thumbnail)
                poster_path = role.get("poster_path")
                if poster_path:
                    try:
                        img_data = requests.get(f"https://image.tmdb.org/t/p/w154{poster_path}").content
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_data)
                        poster_label = QLabel()
                        poster_label.setPixmap(pixmap)
                        role_layout.addWidget(poster_label)
                    except:
                        pass
                
                # Role info with better typography
                role_info = QLabel(
                    f"<p style='color:#FFFFFF; font-size: 15px; margin: 5px 0;'>"
                    f"<b>{role_name}</b> ({role_type})<br>"
                    f"<span style='font-size: 14px; color: #AAAAAA;'>as <i>{character}</i></span></p>"
                )
                role_info.setWordWrap(True)
                role_layout.addWidget(role_info, stretch=1)
                
                known_for_layout.addWidget(role_frame)

        self.content_layout.addWidget(known_for_frame)

        # Gallery section with larger thumbnails
        images = data.get("images", {}).get("profiles", [])
        if images:
            gallery_frame = QFrame()
            gallery_frame.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 15px; margin-top: 15px;")
            gallery_layout = QVBoxLayout(gallery_frame)
            gallery_layout.setContentsMargins(10, 10, 10, 10)
            gallery_layout.setSpacing(15)
            
            gallery_layout.addWidget(QLabel("<h2 style='color:#FF0000; margin-bottom: 10px;'>Gallery</h2>"))

            # Horizontal scroll area for gallery
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setStyleSheet("background: transparent; border: none;")
            
            gallery_widget = QWidget()
            gallery_hbox = QHBoxLayout(gallery_widget)
            gallery_hbox.setContentsMargins(5, 5, 5, 5)
            gallery_hbox.setSpacing(15)
            
            for image in images[:10]:  # Show first 10 images
                try:
                    img_data = requests.get(f"https://image.tmdb.org/t/p/w300{image['file_path']}").content
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    pixmap = pixmap.scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    image_frame = QFrame()
                    image_frame.setStyleSheet("background: transparent;")
                    image_layout = QVBoxLayout(image_frame)
                    image_layout.setContentsMargins(0, 0, 0, 0)
                    
                    poster_label = QLabel()
                    poster_label.setPixmap(pixmap)
                    poster_label.setAlignment(Qt.AlignCenter)
                    image_layout.addWidget(poster_label)
                    
                    gallery_hbox.addWidget(image_frame)
                except:
                    pass
            
            scroll_area.setWidget(gallery_widget)
            gallery_layout.addWidget(scroll_area)
            self.content_layout.addWidget(gallery_frame)

    def display_media_details(self, data):
        title = data.get("title") or data.get("name", "Unknown")
        self.title_label.setText(f"Details - {title}")
        
        # Main content container
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)
        
        # Title with larger font and better spacing
        title_label = QLabel(f"<h1 style='color:#FF0000; margin-bottom: 10px;'>{title}</h1>")
        main_layout.addWidget(title_label)

        # Top section with poster and basic info
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)

        # Poster image (larger size)
        poster_path = data.get("poster_path")
        if poster_path:
            try:
                img_data = requests.get(f"https://image.tmdb.org/t/p/w300{poster_path}").content
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                pixmap = pixmap.scaled(300, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                poster_label = QLabel()
                poster_label.setPixmap(pixmap)
                poster_label.setAlignment(Qt.AlignCenter)
                top_layout.addWidget(poster_label)
            except Exception as e:
                print(f"Error loading poster: {e}")
                error_label = QLabel("Poster unavailable")
                error_label.setStyleSheet("color: #FFFFFF; font-size: 14px;")
                top_layout.addWidget(error_label)

        # Basic info frame
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 15px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(15)

        # Rating with star icon
        rating = data.get("vote_average", 0)
        if rating > 0:
            rating_label = QLabel(
                f"<p style='color:#FFFFFF; font-size: 16px; margin: 5px 0;'>"
                f"<b style='color:#FF0000;'>Rating:</b> ★ {rating:.1}/10</p>"
            )
            info_layout.addWidget(rating_label)

        # Release date
        date = data.get("release_date") or data.get("first_air_date")
        if date:
            date_label = QLabel(
                f"<p style='color:#FFFFFF; font-size: 16px; margin: 5px 0;'>"
                f"<b style='color:#FF0000;'>Release Date:</b> {date}</p>"
            )
            info_layout.addWidget(date_label)

        # Genres
        genres = ", ".join([g["name"] for g in data.get("genres", [])])
        if genres:
            genres_label = QLabel(
                f"<p style='color:#FFFFFF; font-size: 16px; margin: 5px 0;'>"
                f"<b style='color:#FF0000;'>Genres:</b> {genres}</p>"
            )
            info_layout.addWidget(genres_label)

        # Runtime for movies
        runtime = data.get("runtime")
        if runtime:
            hours = runtime // 60
            minutes = runtime % 60
            runtime_label = QLabel(
                f"<p style='color:#FFFFFF; font-size: 16px; margin: 5px 0;'>"
                f"<b style='color:#FF0000;'>Runtime:</b> {hours}h {minutes}m</p>"
            )
            info_layout.addWidget(runtime_label)

        # Number of episodes for TV shows
        num_episodes = data.get("number_of_episodes")
        if num_episodes:
            episodes_label = QLabel(
                f"<p style='color:#FFFFFF; font-size: 16px; margin: 5px 0;'>"
                f"<b style='color:#FF0000;'>Episodes:</b> {num_episodes}</p>"
            )
            info_layout.addWidget(episodes_label)

        top_layout.addWidget(info_frame)
        main_layout.addWidget(top_section)

        # Overview section with better formatting
        overview = data.get("overview", "Not available")
        overview_frame = QFrame()
        overview_frame.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 15px;")
        overview_layout = QVBoxLayout(overview_frame)
        overview_layout.setContentsMargins(10, 10, 10, 10)
        
        overview_label = QLabel("<h3 style='color:#FF0000; margin-bottom: 10px;'>Overview</h3>")
        overview_text = QTextEdit()
        overview_text.setPlainText(overview)
        overview_text.setReadOnly(True)
        overview_text.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: none;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
            }
        """)
        
        overview_layout.addWidget(overview_label)
        overview_layout.addWidget(overview_text)
        main_layout.addWidget(overview_frame)

        # Cast section with improved layout
        if "credits" in data:
            cast_frame = QFrame()
            cast_frame.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 15px;")
            cast_layout = QVBoxLayout(cast_frame)
            cast_layout.setContentsMargins(10, 10, 10, 10)
            cast_layout.setSpacing(15)
            
            cast_layout.addWidget(QLabel("<h3 style='color:#FF0000; margin-bottom: 10px;'>Cast</h3>"))
            
            # Horizontal scroll area for cast
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setStyleSheet("background: transparent; border: none;")
            
            cast_widget = QWidget()
            cast_hbox = QHBoxLayout(cast_widget)
            cast_hbox.setContentsMargins(5, 5, 5, 5)
            cast_hbox.setSpacing(15)
            
            for cast_member in data["credits"].get("cast", [])[:10]:  # Show first 10 cast members
                cast_member_frame = QFrame()
                cast_member_frame.setStyleSheet("background: #333333; border-radius: 8px; padding: 10px;")
                cast_member_layout = QVBoxLayout(cast_member_frame)
                cast_member_layout.setContentsMargins(10, 10, 10, 10)
                cast_member_layout.setSpacing(10)
                
                # Cast member image
                profile_path = cast_member.get("profile_path")
                if profile_path:
                    try:
                        img_data = requests.get(f"https://image.tmdb.org/t/p/w185{profile_path}").content
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_data)
                        pixmap = pixmap.scaled(150, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        
                        poster_label = QLabel()
                        poster_label.setPixmap(pixmap)
                        poster_label.setAlignment(Qt.AlignCenter)
                        cast_member_layout.addWidget(poster_label)
                    except:
                        pass
                
                # Cast member info
                name = cast_member.get("name", "Unknown")
                character = cast_member.get("character", "Unknown")
                
                name_label = QLabel(f"<b style='color:#FFFFFF; font-size: 14px;'>{name}</b>")
                name_label.setAlignment(Qt.AlignCenter)
                name_label.setWordWrap(True)
                
                character_label = QLabel(f"<span style='color:#AAAAAA; font-size: 13px;'>as {character}</span>")
                character_label.setAlignment(Qt.AlignCenter)
                character_label.setWordWrap(True)
                
                cast_member_layout.addWidget(name_label)
                cast_member_layout.addWidget(character_label)
                cast_hbox.addWidget(cast_member_frame)
            
            scroll_area.setWidget(cast_widget)
            cast_layout.addWidget(scroll_area)
            main_layout.addWidget(cast_frame)

        # Watch providers section
        if "watch/providers" in data and "US" in data["watch/providers"].get("results", {}):
            providers_frame = QFrame()
            providers_frame.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 15px;")
            providers_layout = QVBoxLayout(providers_frame)
            providers_layout.setContentsMargins(10, 10, 10, 10)
            
            providers_layout.addWidget(QLabel("<h3 style='color:#FF0000; margin-bottom: 10px;'>Where to Watch</h3>"))
            
            providers = data["watch/providers"]["results"]["US"].get("flatrate", [])
            if providers:
                providers_hbox = QHBoxLayout()
                providers_hbox.setContentsMargins(10, 10, 10, 10)
                providers_hbox.setSpacing(15)
                
                for provider in providers[:6]:  # Show first 6 providers
                    provider_frame = QFrame()
                    provider_frame.setStyleSheet("background: #333333; border-radius: 8px; padding: 10px;")
                    provider_layout = QVBoxLayout(provider_frame)
                    provider_layout.setContentsMargins(10, 10, 10, 10)
                    provider_layout.setSpacing(10)
                    
                    # Provider logo
                    logo_path = provider.get("logo_path")
                    if logo_path:
                        try:
                            img_data = requests.get(f"https://image.tmdb.org/t/p/w154{logo_path}").content
                            pixmap = QPixmap()
                            pixmap.loadFromData(img_data)
                            pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            
                            logo_label = QLabel()
                            logo_label.setPixmap(pixmap)
                            logo_label.setAlignment(Qt.AlignCenter)
                            provider_layout.addWidget(logo_label)
                        except:
                            pass
                    
                    # Provider name
                    name_label = QLabel(provider.get("provider_name", "Unknown"))
                    name_label.setStyleSheet("color: #FFFFFF; font-size: 14px;")
                    name_label.setAlignment(Qt.AlignCenter)
                    provider_layout.addWidget(name_label)
                    
                    providers_hbox.addWidget(provider_frame)
                
                providers_layout.addLayout(providers_hbox)
                main_layout.addWidget(providers_frame)

        # Recommendations section
        if "recommendations" in data and data["recommendations"].get("results"):
            recs_frame = QFrame()
            recs_frame.setStyleSheet("background-color: #222222; border-radius: 8px; padding: 15px;")
            recs_layout = QVBoxLayout(recs_frame)
            recs_layout.setContentsMargins(10, 10, 10, 10)
            recs_layout.setSpacing(15)
            
            recs_layout.addWidget(QLabel("<h3 style='color:#FF0000; margin-bottom: 10px;'>Recommendations</h3>"))
            
            # Horizontal scroll area for recommendations
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setStyleSheet("background: transparent; border: none;")
            
            recs_widget = QWidget()
            recs_hbox = QHBoxLayout(recs_widget)
            recs_hbox.setContentsMargins(5, 5, 5, 5)
            recs_hbox.setSpacing(15)
            
            for rec in data["recommendations"]["results"][:10]:  # Show first 10 recommendations
                rec_frame = QFrame()
                rec_frame.setStyleSheet("background: #333333; border-radius: 8px; padding: 10px;")
                rec_layout = QVBoxLayout(rec_frame)
                rec_layout.setContentsMargins(10, 10, 10, 10)
                rec_layout.setSpacing(10)
                
                # Recommendation poster
                poster_path = rec.get("poster_path")
                if poster_path:
                    try:
                        img_data = requests.get(f"https://image.tmdb.org/t/p/w185{poster_path}").content
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_data)
                        pixmap = pixmap.scaled(150, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        
                        poster_label = QLabel()
                        poster_label.setPixmap(pixmap)
                        poster_label.setAlignment(Qt.AlignCenter)
                        rec_layout.addWidget(poster_label)
                    except:
                        pass
                
                # Recommendation title
                rec_title = rec.get("title") or rec.get("name", "Unknown")
                title_label = QLabel(f"<b style='color:#FFFFFF; font-size: 14px;'>{rec_title}</b>")
                title_label.setAlignment(Qt.AlignCenter)
                title_label.setWordWrap(True)
                
                # Recommendation rating
                vote_avg = rec.get("vote_average", 0)
                if vote_avg > 0:
                    rating_label = QLabel(f"<span style='color:#FF0000; font-size: 13px;'>★ {vote_avg:.1}</span>")
                    rating_label.setAlignment(Qt.AlignCenter)
                    rec_layout.addWidget(rating_label)
                
                rec_layout.addWidget(title_label)
                rec_hbox.addWidget(rec_frame)
            
            scroll_area.setWidget(recs_widget)
            recs_layout.addWidget(scroll_area)
            main_layout.addWidget(recs_frame)

        # Add main container to content layout
        self.content_layout.addWidget(main_container)

# Main GUI class for the WatchX application
class TMDbGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WatchX")
        self.setGeometry(100, 100, 1280, 900)  # Larger default window size
        self.setMinimumSize(1024, 768)  # Minimum size to ensure proper layout
        
        # Enhanced style sheet with better typography and spacing
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
            }
            QPushButton {
                background-color: #FF0000;
                color: #FFFFFF;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
            QLineEdit {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
                border-radius: 15px;
                padding: 8px 20px;
                font-size: 14px;
            }
            QComboBox {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
                padding: 8px;
                font-size: 14px;
                min-width: 120px;
            }
            QComboBox QAbstractItemView {
                background-color: #222222;
                color: #FFFFFF;
                selection-background-color: #FF0000;
                font-size: 14px;
            }
            QTabWidget::pane {
                border: none;
                background: #121212;
            }
            QTabBar::tab {
                background: #222222;
                color: #FFFFFF;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: #FF0000;
                color: #FFFFFF;
            }
            QScrollArea {
                background: #121212;
                border: none;
            }
            QStatusBar {
                background: #222222;
                color: #FFFFFF;
                font-size: 13px;
            }
            QListWidget {
                background-color: #222222;
                color: #FFFFFF;
                border: 1px solid #FF0000;
                font-size: 14px;
            }
        """)

        # Set default font for the application
        font = QFont()
        font.setFamily("Arial")
        self.setFont(font)

        # Load API keys from .env file
        load_dotenv()
        self.tmdb_api_key = os.getenv("TMDB_API_KEY")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")

        if not all([self.tmdb_api_key, self.youtube_api_key, self.rapidapi_key]):
            print("Error: Missing API keys in .env file")
            sys.exit(1)

        # Initialize variables and caches
        self.tmdb_image_base_url = "https://image.tmdb.org/t/p/w300"  # Higher resolution images
        self.trailer_cache = {}
        self.streaming_cache = {}
        self.logged_in = False
        self.username = None
        self.favorites = []  # Local list for favorited items

        # Set up central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

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
        header.setStyleSheet("background-color: #222222; padding: 15px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        header_layout.setSpacing(20)

        # Logo with larger font and better styling
        logo_label = QLabel("WATCHX")
        logo_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            color: #FF0000;
            padding: 5px 10px;
        """)
        header_layout.addWidget(logo_label)

        # Navigation buttons for categories with better styling
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(15)
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
                    font-size: 16px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    color: #FF0000;
                }
            """)
            btn.clicked.connect(lambda checked, c=category: self.switch_category(c))
            self.nav_buttons[category] = btn
            nav_layout.addWidget(btn)
        header_layout.addLayout(nav_layout)

        # Search bar with content type selector - improved styling
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        self.search_type = QComboBox()
        self.search_type.addItems(["Movies", "TV Shows", "People"])
        self.search_type.setStyleSheet("""
            QComboBox {
                min-width: 100px;
            }
        """)
        search_layout.addWidget(self.search_type)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search movies, TV shows, people...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                min-width: 250px;
            }
        """)
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.setStyleSheet("""
            QPushButton {
                background: #FF0000; 
                color: white; 
                border-radius: 15px; 
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #CC0000;
            }
        """)
        search_btn.clicked.connect(self.search_content)
        search_layout.addWidget(search_btn)
        header_layout.addLayout(search_layout)

        # Login and Join buttons with better styling
        auth_layout = QHBoxLayout()
        auth_layout.setSpacing(10)
        
        self.login_btn = QPushButton("Login")
        self.join_btn = QPushButton("Join TMDb")
        
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: none;
                color: #FFFFFF;
                border: none;
                font-size: 14px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                color: #FF0000;
            }
        """)
        
        self.join_btn.setStyleSheet("""
            QPushButton {
                background: #FF0000; 
                color: white; 
                border-radius: 5px; 
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #CC0000;
            }
        """)
        
        self.login_btn.clicked.connect(self.show_login_dialog)
        self.join_btn.clicked.connect(lambda: webbrowser.open("https://www.themoviedb.org/signup"))
        
        auth_layout.addWidget(self.login_btn)
        auth_layout.addWidget(self.join_btn)
        header_layout.addLayout(auth_layout)

        self.main_layout.addWidget(header)

    # Sets up the main content section with tabs and filter
    def setup_content_section(self):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(15)

        # Content title with larger font
        self.content_label = QLabel("Trending Movies")
        self.content_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #FF0000;
            margin-bottom: 10px;
        """)
        content_layout.addWidget(self.content_label)

        # Filter combo box for content types with better styling
        self.filter_combo = QComboBox()
        self.filter_combo.setStyleSheet("""
            QComboBox {
                max-width: 200px;
                font-size: 14px;
            }
        """)
        content_layout.addWidget(self.filter_combo)

        # Tabs for Today and This Week views with better styling
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #121212;
            }
            QTabBar::tab {
                background: #222222;
                color: #FFFFFF;
                padding: 10px 25px;
                border-radius: 5px;
                font-size: 14px;
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

        # Scrollable areas for content grids with better styling
        self.today_scroll = QScrollArea()
        self.today_scroll.setWidgetResizable(True)
        self.today_content = QWidget()
        self.today_content.setStyleSheet("background-color: #121212;")
        self.today_grid = QGridLayout(self.today_content)
        self.today_grid.setContentsMargins(10, 10, 10, 10)
        self.today_grid.setSpacing(20)
        self.today_scroll.setWidget(self.today_content)
        
        self.today_tab.setLayout(QVBoxLayout())
        self.today_tab.layout().setContentsMargins(0, 0, 0, 0)
        self.today_tab.layout().addWidget(self.today_scroll)

        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_content = QWidget()
        self.week_content.setStyleSheet("background-color: #121212;")
        self.week_grid = QGridLayout(self.week_content)
        self.week_grid.setContentsMargins(10, 10, 10, 10)
        self.week_grid.setSpacing(20)
        self.week_scroll.setWidget(self.week_content)
        
        self.week_tab.setLayout(QVBoxLayout())
        self.week_tab.layout().setContentsMargins(0, 0, 0, 0)
        self.week_tab.layout().addWidget(self.week_scroll)

        self.main_layout.addWidget(content_widget)

    # Sets up footer with action buttons
    def setup_footer(self):
        footer = QFrame()
        footer.setStyleSheet("""
            background-color: #222222; 
            padding: 15px;
            border-top: 1px solid #FF0000;
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(30, 10, 30, 10)
        footer_layout.setSpacing(20)

        footer_items = {
            "🎬 Latest Trailers": self.show_latest_trailers,
            "🔥 Popular": lambda: self.load_content(self.current_content_type, "popular", "day"),
            "📺 Streaming": lambda: self.load_content(self.current_content_type, "trending", "day"),
            "📡 On TV": lambda: self.load_content("tv", "airing_today", "day"),
            "💵 For Rent": lambda: self.load_content(self.current_content_type, "trending", "day"),
            "🎭 In Theatres": lambda: self.load_content("movie", "now_playing", "day")
        }
        
        for text, action in footer_items.items():
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: #333333;
                    color: #FFFFFF;
                    border-radius: 15px;
                    padding: 8px 15px;
                    font-size: 14px;
                    min-width: 120px;
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
                self.login_btn.setText(f"👤 {username}")
                self.login_btn.setStyleSheet("""
                    QPushButton {
                        background: none;
                        color: #FF0000;
                        border: none;
                        font-size: 14px;
                        padding: 5px 10px;
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
                font-size: 14px;
                padding: 5px 10px;
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
        
        # Only disconnect if there are connections
        try:
            self.filter_combo.currentTextChanged.disconnect()
        except TypeError:
            pass  # No connections to disconnect
        
        for opt in self.nav_options[category]:
            self.filter_combo.addItem(opt[0], opt[1])
        
        self.filter_combo.currentTextChanged.connect(
            lambda text: self.load_content(self.current_content_type, self.filter_combo.currentData(), "day")
        )
        
        # Load the first option by default
        self.load_content(self.current_content_type, self.nav_options[category][0][1], "day")
        
        # Update button styles to show active category
        for btn_category, btn in self.nav_buttons.items():
            btn.setStyleSheet("""
                QPushButton {
                    color: #FFFFFF;
                    background: none;
                    border: none;
                    font-size: 16px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    color: #FF0000;
                }
            """ if btn_category != category else """
                QPushButton {
                    color: #FF0000;
                    background: none;
                    border-bottom: 2px solid #FF0000;
                    font-size: 16px;
                    padding: 5px 10px;
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

    # Displays fetched content in the grid with improved styling
    def display_content(self, data):
        target_grid = self.today_grid if "day" in self.worker.url or "trending" not in self.worker.url else self.week_grid
        self.clear_layout(target_grid)
        items = data.get("results", [])
        self.status_bar.showMessage(f"Loaded {len(items)} items" if items else "Failed to load content")

        if not items:
            error_label = QLabel("No results found or failed to load content.")
            error_label.setStyleSheet("color: #FF0000; font-size: 16px;")
            error_label.setAlignment(Qt.AlignCenter)
            target_grid.addWidget(error_label, 0, 0, 1, 4)
            return

        items = items[:12]  # Limit to 12 items for better display
        for i, item in enumerate(items):
            item_widget = QWidget()
            item_widget.setStyleSheet("""
                background-color: #222222; 
                border-radius: 10px; 
                padding: 15px;
            """)
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(10)

            # Load and display image with better sizing
            image_path = item.get("poster_path") or item.get("profile_path")
            if image_path:
                try:
                    img_data = requests.get(f"{self.tmdb_image_base_url}{image_path}").content
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    
                    # Larger images for better visibility
                    if self.current_content_type == "person":
                        pixmap = pixmap.scaled(200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    else:
                        pixmap = pixmap.scaled(220, 330, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    poster_label = QLabel()
                    poster_label.setPixmap(pixmap)
                    poster_label.setAlignment(Qt.AlignCenter)
                    item_layout.addWidget(poster_label)
                except Exception as e:
                    print(f"Error loading image: {e}")
                    poster_label = QLabel("Image unavailable")
                    poster_label.setStyleSheet("color: #FFFFFF; font-size: 14px;")
                    poster_label.setAlignment(Qt.AlignCenter)
                    item_layout.addWidget(poster_label)

            # Content specific information with better typography
            if self.current_content_type == "person":
                # People display
                name = item.get("name", "Unknown")
                title_label = QLabel(name)
                title_label.setStyleSheet("""
                    font-size: 16px; 
                    font-weight: bold; 
                    color: #FFFFFF;
                    margin-top: 5px;
                """)
                title_label.setWordWrap(True)
                title_label.setAlignment(Qt.AlignCenter)
                item_layout.addWidget(title_label)

                known_for = item.get("known_for", [])
                if known_for:
                    known_for_text = ", ".join([x.get("title") or x.get("name") or "Unknown" for x in known_for[:2]])
                    known_label = QLabel(known_for_text)
                    known_label.setStyleSheet("""
                        font-size: 14px; 
                        color: #AAAAAA;
                        margin-bottom: 5px;
                    """)
                    known_label.setWordWrap(True)
                    known_label.setAlignment(Qt.AlignCenter)
                    item_layout.addWidget(known_label)
            else:
                # Movie/TV show display
                rating = item.get("vote_average", 0) * 10 if "vote_average" in item else None
                if rating is not None:
                    rating_label = QLabel(f"★ {int(rating)}%")
                    rating_label.setStyleSheet("""
                        font-size: 16px; 
                        font-weight: bold; 
                        color: #FF0000;
                        margin-top: 5px;
                    """)
                    rating_label.setAlignment(Qt.AlignCenter)
                    item_layout.addWidget(rating_label)

                title = item.get("title") or item.get("name", "Unknown")
                title_label = QLabel(title)
                title_label.setStyleSheet("""
                    font-size: 16px; 
                    font-weight: bold; 
                    color: #FFFFFF;
                """)
                title_label.setWordWrap(True)
                title_label.setAlignment(Qt.AlignCenter)
                item_layout.addWidget(title_label)

                date = item.get("release_date") or item.get("first_air_date", "N/A")
                date_label = QLabel(date)
                date_label.setStyleSheet("""
                    font-size: 14px; 
                    color: #AAAAAA;
                    margin-bottom: 5px;
                """)
                date_label.setAlignment(Qt.AlignCenter)
                item_layout.addWidget(date_label)

            # Common buttons with better styling
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(10)

            item_id = item.get("id")
            title = item.get("title") or item.get("name", "Unknown")
            
            detail_btn = QPushButton("Details")
            detail_btn.setStyleSheet("""
                QPushButton {
                    background: #FF0000;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #CC0000;
                }
            """)
            detail_btn.clicked.connect(lambda checked, ct=self.current_content_type, id=item_id: DetailDialog(ct, id, self.tmdb_api_key, self).exec_())
            button_layout.addWidget(detail_btn)

            fav_btn = QPushButton("❤ Favorite" if item_id not in self.favorites else "★ Unfavorite")
            fav_btn.setStyleSheet("""
                QPushButton {
                    background: #333333;
                    color: white;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #444444;
                }
            """)
            fav_btn.clicked.connect(lambda checked, id=item_id, t=title, b=fav_btn: self.toggle_favorite(id, t, b))
            button_layout.addWidget(fav_btn)

            item_layout.addWidget(button_container)

            # Calculate grid position (3 columns)
            row = i // 3
            col = i % 3
            target_grid.addWidget(item_widget, row, col, 1, 1, Qt.AlignTop)

    # Toggles an item as a favorite and updates UI
    def toggle_favorite(self, item_id, title, button):
        if item_id in self.favorites:
            self.favorites.remove(item_id)
            button.setText("❤ Favorite")
            self.status_bar.showMessage(f"Removed '{title}' from favorites")
        else:
            self.favorites.append(item_id)
            button.setText("★ Unfavorite")
            self.status_bar.showMessage(f"Added '{title}' to favorites")

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
