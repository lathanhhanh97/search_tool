import sys
from PyQt5.QtWidgets import QApplication
from search_tool.gui import WifiWidget

if __name__ == '__main__':
    app = QApplication(sys.argv)
    wifi_widget = WifiWidget()
    wifi_widget.show()
    sys.exit(app.exec_())
