from PySide6.QtCore import (
    QSize, 
    Qt,
    QPoint
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel
)
from PySide6.QtGui import (
    QGuiApplication
)

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("My App")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(QSize(300, 130))
        
        layout = QVBoxLayout()

        label = QLabel("Оцените ваше самочувствие")
        label.setMinimumSize(250, 0)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        button_1 = QPushButton("Хорошее")
        button_2 = QPushButton("Нейтральное")
        button_3 = QPushButton("Плохое")
        layout.addWidget(button_1)
        layout.addWidget(button_2)
        layout.addWidget(button_3)

        widget = QWidget()
        widget.setLayout(layout)
        self.bottomRight()
        # Set the central widget of the Window.
        self.setCentralWidget(widget)

    def bottomRight(self):
        bottpmRightPoint = QGuiApplication.primaryScreen().availableGeometry().bottomRight()
        size = self.size()
        bottpmRightPoint -= QPoint(size.width()+30, size.height()+50)
        self.move(bottpmRightPoint)


if __name__ == '__main__':
    app = QApplication()

    window = MainWindow()
    window.show()

    app.exec_()
