import asyncio
import logging

from PyQt5.QtCore import Qt, QTime, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QFontMetrics, QPainter, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStatusBar,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from feeluown import __upgrade_desc__
from feeluown.components.cmdbox import CmdBox
from feeluown.components.separator import Separator
from feeluown.components.playlists import (
    PlaylistsView,
    PlaylistsModel,
)
from feeluown.components.library import LibrariesView
from feeluown.components.history import HistoriesView
from feeluown.containers.table_container import SongsTableContainer

from .consts import PlaybackMode
from .utils import parse_ms


logger = logging.getLogger(__name__)


class VolumeSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setOrientation(Qt.Horizontal)
        #self.setRange(0, 100)   # player volume range
        #self.setValue(100)
        self.setToolTip('调教播放器音量')


class ProgressSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setOrientation(Qt.Horizontal)

    def set_duration(self, ms):
        self.setRange(0, ms / 1000)

    def update_state(self, ms):
        self.setValue(ms / 1000)


class PlayerControlPanel(QFrame):

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        class Button(QPushButton):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                # self.setFixedSize(40, 40)
                self.setMaximumWidth(40)

        # initialize sub widgets
        self._layout = QHBoxLayout(self)
        self.previous_btn = Button(self)
        self.pp_btn = Button(self)
        self.next_btn = Button(self)
        self.pms_btn = Button(self)
        self.volume_btn = Button(self)
        self.playlist_btn = Button('🎶', self)

        self.pms_btn.setToolTip('该功能尚未开发完成，欢迎 PR')
        self.volume_btn.setToolTip('该功能尚未开发完成，欢迎 PR')
        self.playlist_btn.setToolTip('显示当前播放列表')

        self.previous_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.pp_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.next_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.volume_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))

        self.song_title_label = QLabel('No song is playing.', parent=self)
        self.song_title_label.setAlignment(Qt.AlignCenter)
        self.duration_label = QLabel('00:00', parent=self)
        self.position_label = QLabel('00:00', parent=self)
        self.progress_slider = ProgressSlider(self)

        self.next_btn.clicked.connect(self._app.player.playlist.play_next)
        self.previous_btn.clicked.connect(self._app.player.playlist.play_previous)
        self.pp_btn.clicked.connect(self._app.player.toggle)

        # set widget layout
        self.progress_slider.setMinimumWidth(480)
        self.progress_slider.setMaximumWidth(600)
        self.progress_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._sub_layout = QVBoxLayout()
        self._sub_layout.addWidget(self.song_title_label)
        self._sub_layout.addWidget(self.progress_slider)

        self._layout.addSpacing(10)
        self._layout.addWidget(self.previous_btn)
        self._layout.addWidget(self.pp_btn)
        self._layout.addWidget(self.next_btn)
        self._layout.addSpacing(15)
        self._layout.addStretch(0)
        self._layout.addWidget(self.position_label)
        self._layout.addSpacing(7)
        self._layout.addLayout(self._sub_layout)
        self._layout.addSpacing(7)
        self._layout.addWidget(self.duration_label)
        self._layout.addSpacing(5)
        self._layout.addStretch(0)
        self._layout.addWidget(self.volume_btn)
        self._layout.addSpacing(10)
        self._layout.addWidget(self.pms_btn)
        self._layout.addWidget(self.playlist_btn)
        self._layout.addSpacing(10)

        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def on_duration_changed(self, duration):
        m, s = parse_ms(duration)
        t = QTime(0, m, s)
        self.duration_label.setText(t.toString('mm:ss'))

    def on_position_changed(self, position):
        m, s = parse_ms(position)
        t = QTime(0, m, s)
        self.position_label.setText(t.toString('mm:ss'))

    def on_playback_mode_changed(self, playback_mode):
        self.pms_btn.setText(playback_mode.value)

    def on_player_song_changed(self, song):
        self.song_title_label.setText(
            '♪  {title} - {artists_name}'.format(
                title=song.title,
                artists_name=song.artists_name))


class TopPanel(QFrame):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        self._layout = QHBoxLayout(self)
        self.pc_panel = PlayerControlPanel(self._app, self)
        self.setObjectName('top_panel')

        self.setFixedHeight(60)

        self._layout.addWidget(self.pc_panel)


class LeftPanel(QFrame):

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        self.library_header = QLabel('我的音乐', self)
        self.playlists_header = QLabel('歌单列表', self)
        self.history_header = QLabel('浏览历史记录', self)

        self.playlists_view = PlaylistsView(self)
        self.libraries_view = LibrariesView(self)
        self.histories_view = HistoriesView(self)
        self._splitter = QSplitter(Qt.Vertical, self)

        self.libraries_view.setModel(self._app.libraries)
        self.histories_view.setModel(self._app.histories)

        self._layout = QVBoxLayout(self)
        self._splitter.addWidget(self.library_header)
        self._splitter.addWidget(self.libraries_view)
        self._splitter.addWidget(self.history_header)
        self._splitter.addWidget(self.histories_view)
        self._splitter.addWidget(self.playlists_header)
        self._splitter.addWidget(self.playlists_view)
        self._layout.addWidget(self._splitter)

        self.libraries_view.setFrameShape(QFrame.NoFrame)
        self.playlists_view.setFrameShape(QFrame.NoFrame)
        self.histories_view.setFrameShape(QFrame.NoFrame)
        self.setMinimumWidth(180)
        self.setMaximumWidth(250)

        self.playlists_view.show_playlist.connect(
            lambda pl: asyncio.ensure_future(self.show_model(pl)))
        self.histories_view.show_model.connect(
            lambda model: asyncio.ensure_future(self.show_model(model)))

    def set_playlists(self, playlists):
        model = PlaylistsModel(playlists, self)
        self.playlists_view.setModel(model)

    async def show_model(self, playlist):
        await self._app.ui.table_container.show_model(playlist)


class RightPanel(QFrame):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        self._layout = QHBoxLayout(self)
        self.table_container = SongsTableContainer(self._app, self)
        self._layout.addWidget(self.table_container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)


class SongLabel(QLabel):
    def __init__(self, text=None, parent=None):
        super().__init__(text, parent)
        self.set_song('No song is playing')

    def set_song(self, song_text):
        self.setText('♪  ' + song_text + ' ')


class MessageLabel(QLabel):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app

        self.setObjectName('message_label')
        self._interval = 3
        self.timer = QTimer()
        self.queue = []
        self.hide()

        self.timer.timeout.connect(self.access_message_queue)

    @property
    def common_style(self):
        style_str = '''
            #{0} {{
                padding-left: 3px;
                padding-right: 5px;
            }}
        '''.format(self.objectName())
        return style_str

    def _set_error_style(self):
        theme = self._app.theme_manager.current_theme
        style_str = '''
            #{0} {{
                background: {1};
                color: {2};
            }}
        '''.format(self.objectName(),
                   theme.color1_light.name(),
                   theme.color7_light.name())
        self.setStyleSheet(style_str + self.common_style)

    def _set_normal_style(self):
        theme = self._app.theme_manager.current_theme
        style_str = '''
            #{0} {{
                background: {1};
                color: {2};
            }}
        '''.format(self.objectName(),
                   theme.color6_light.name(),
                   theme.color7.name())
        self.setStyleSheet(style_str + self.common_style)

    def show_message(self, text, error=False):
        if self.isVisible():
            self.queue.append({'error': error, 'message': text})
            self._interval = 1.5
            return
        if error:
            self._set_error_style()
        else:
            self._set_normal_style()
        self.setText(str(len(self.queue)) + ': ' + text)
        self.show()
        self.timer.start(self._interval * 1000)

    def access_message_queue(self):
        self.hide()
        if self.queue:
            m = self.queue.pop(0)
            self.show_message(m['message'], m['error'])
        else:
            self._interval = 3


class NetworkStatus(QLabel):
    def __init__(self, app, text=None, parent=None):
        super().__init__(text, parent)
        self._app = app

        self.setToolTip('这里显示的是当前网络状态')
        self.setObjectName('network_status_label')
        self._progress = 100
        self._show_progress = False

        self.set_state(1)

    def paintEvent(self, event):
        if self._show_progress:
            painter = QPainter(self)
            p_bg_color = self._app.theme_manager.current_theme.color0
            painter.fillRect(self.rect(), p_bg_color)
            bg_color = self._app.theme_manager.current_theme.color3
            rect = self.rect()
            percent = self._progress * 1.0 / 100
            rect.setWidth(int(rect.width() * percent))
            painter.fillRect(rect, bg_color)
            painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignHCenter,
                             str(self._progress) + '%')
            self._show_progress = False
        else:
            super().paintEvent(event)

    @property
    def common_style(self):
        theme = self._app.theme_manager.current_theme
        style_str = '''
            #{0} {{
                background: {1};
                color: {2};
                padding-left: 5px;
                padding-right: 5px;
                font-size: 14px;
                font-weight: bold;
            }}
        '''.format(self.objectName(),
                   theme.color3.name(),
                   theme.background.name())
        return style_str

    def set_theme_style(self):
        self.setStyleSheet(self.common_style)

    def _set_error_style(self):
        theme = self._app.theme_manager.current_theme
        style_str = '''
            #{0} {{
                background: {1};
            }}
        '''.format(self.objectName(),
                   theme.color5.name())
        self.setStyleSheet(self.common_style + style_str)

    def _set_normal_style(self):
        self.setStyleSheet(self.common_style)

    def set_state(self, state):
        if state == 0:
            self._set_error_style()
            self.setText('✕')
        elif state == 1:
            self._set_normal_style()
            self.setText('✓')

    def show_progress(self, progress):
        self._progress = progress
        self._show_progress = True
        if self._progress == 100:
            self._show_progress = False
        self.update()


class Ui(object):
    def __init__(self, app):
        self._app = app
        self._layout = QVBoxLayout(app)
        self._bottom_layout = QHBoxLayout()
        self._top_separator = Separator(app)
        self._splitter = QSplitter(app)

        # NOTE: 以位置命名的部件应该只用来组织界面布局，不要
        # 给其添加任何功能性的函数
        self.top_panel = TopPanel(app, app)
        self.left_panel = LeftPanel(self._app, self._splitter)
        self.right_panel = RightPanel(self._app, self._splitter)

        # alias
        self.pc_panel = self.top_panel.pc_panel
        self.table_container = self.right_panel.table_container
        self.cmdbox = CmdBox(self._app)

        # 对部件进行一些 UI 层面的初始化
        self._splitter.addWidget(self.left_panel)
        self._splitter.addWidget(self.right_panel)
        self.cmdbox.setFrame(False)

        self.right_panel.setMinimumWidth(780)
        self.left_panel.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._layout.addWidget(self.top_panel)
        self._layout.addWidget(self._top_separator)
        self._layout.addWidget(self._splitter)
        self._layout.addWidget(self.cmdbox)

        # self._layout.addLayout(self._bottom_layout)
        # self._bottom_layout.addWidget(self.cmdbox)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.top_panel.layout().setSpacing(0)
        self.top_panel.layout().setContentsMargins(0, 0, 0, 0)

        self.cmdbox.textEdited.connect(self.table_container.search)
        self.cmdbox.returnPressed.connect(self.search_library)
        self.pc_panel.playlist_btn.clicked.connect(self.show_current_playlist)

        self._app.hotkey_manager.registe(
            [QKeySequence('Ctrl+F'), QKeySequence(':'), QKeySequence('Alt+x')],
            self.cmdbox.setFocus
        )

    def search_library(self):
        text = self.cmdbox.text()
        songs = self._app.provider_manager.search(text)
        self.table_container.show_songs(songs)

    def show_current_playlist(self):
        songs = self._app.playlist.list()
        self.table_container.show_songs(songs)
