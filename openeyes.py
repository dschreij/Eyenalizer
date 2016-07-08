# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 15:41:55 2015

@author: Daniel Schreij & Artem Belopolsky
"""
# Python 3 compatibility
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Use Python3 string instead of deprecated QString
import sip
sip.setapi('QString', 2)

# Tables for HDF5 file handling
import pandas as pd
# Set default from fixed to table format (Enables append)
pd.set_option('io.hdf.default_format','table')

import sys
import os

# Gui componentes
from qtpy import QtCore, QtGui, QtWidgets, uic

__authors__ = "Artem Belopolsky & Daniel Schreij"
__version__ = "0.1.0"

def get_resource_loc(item):
	"""
	Determines the correct path to the required resource.
	When the app is packaged with py2exe or py2app, the locations of some images
	or resources may change. This function should correct for that
	
	Arguments:
		item (string)  - the item to locate
		
	Returns:
		(string) - the full path to the provided item
	
	"""
	
	# When the app is packaged with py2app/exe or pyinstaller
	if getattr(sys, 'frozen', None):
		try:
			# If packaged with pyinstaller
			basedir = sys._MEIPASS		
			return os.path.join(basedir,item)			
		except:
			# If packaged with py2exe (but should also work for py2installer (not tested!) )
			basedir = os.path.dirname(sys.executable, sys.getfilesystemencoding())
			if sys.platform == "win32":
				return os.path.join(basedir, "resources", item)
			elif sys.platform == "darwin":
				return os.path.join(basedir, "..", "Resources", "resources", item)
	# When run from source
	else:
		basedir = os.path.dirname(__file__)
		return os.path.join(basedir,"resources",item)

class Output:
	"""
	Class that intercepts stdout and stderr prints, and shows them in te QT
	textarea of the app.
	"""
	def __init__(self, statusBox, out=None, color=None):
		"""(statusBox, out=None, color=None) -> can write stdout, stderr to a
		QTextEdit.
		edit = QTextEdit
		out = alternate stream ( can be the original sys.stdout )
		color = alternate color (i.e. color stderr a different color)
		"""
		self.statusBox = statusBox
		self.out = out
		self.color = color

	def write(self, m):
		#self.statusBox.moveCursor(QtWidgets.QTextCursor.End)
		if self.color:
			self.statusBox.setTextColor(self.color)

		self.statusBox.insertPlainText( m )
		# Make sure the messages are immediately shown
		QtWidgets.QCoreApplication.instance().processEvents()

		if self.out:
			self.out.write(m)
			
	def flush(self):
		if hasattr(self.out,"flush"):
			self.out.flush()

class OpenEyesGUI(QtWidgets.QMainWindow):
	def __init__(self):
		# Create temporary hdf_file to store data in
		self.TEMPFILENAME = "temp.h5"
		self.tempfile_path = os.path.abspath(self.TEMPFILENAME)
		self.current_datafile = self.TEMPFILENAME
		
		self.hdf5_file = pd.HDFStore(self.tempfile_path)

		app = QtWidgets.QApplication(sys.argv)
		self.ui = self._initUI()	
		exitcode = app.exec_()
		
		if self.hdf5_file.is_open:
			self.hdf5_file.close()
		
		# Clean up temp files
#		if os.path.exists(self.tempfile_path) and os.path.isfile(self.tempfile_path):
#			os.remove(self.tempfile_path)
		
		sys.exit(exitcode)
	
	def _initUI(self):
		"""
		Initializes the UI and sets button actions
		"""							
		QtWidgets.QMainWindow.__init__(self)
		
		# Load resources							
		ui_path = get_resource_loc("firstdraft.ui")

		# Load and setup UI
		ui = uic.loadUi(ui_path)
		ui.setWindowTitle('Open Eyes')		
		ui.show()
		
		# Connect menu buttons to functions
		ui.actionImport.triggered.connect(self.importFiles)
		ui.actionOpen.triggered.connect(self.openFile)		
		ui.toggleFilesWidget.toggled.connect(self.toggleDockWidget)
		ui.toggleOutputWidget.toggled.connect(self.toggleDockWidget)
		
		# Connect other events
		ui.filesWidget.visibilityChanged.connect(self.setDockWidgetVisibility)
		ui.outputWidget.visibilityChanged.connect(self.setDockWidgetVisibility)
		
		# Redirect console output to textbox in UI, printing stdout in black
		# and stderr in red
		sys.stdout = Output(ui.statusBox, sys.stdout, QtGui.QColor(0,0,0))
		if not hasattr(sys,'frozen'):
			sys.stderr = Output(ui.statusBox, sys.stderr, QtGui.QColor(255,0,0))
		else:
			sys.stderr = Output(ui.statusBox, None, QtGui.QColor(255,0,0))
		
		ui.statusBar().showMessage('Ready')
		return ui
		
	def openFile(self):
		# Open file, start in home folder of user
		self.filePath = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", QtCore.QDir.homePath())
		if self.filePath != "":
			if os.path.exists(self.filePath) and os.path.isfile(self.filePath):
				print("Loaded " + self.filePath)		
				# Add filename to filetree		
				filename = os.path.split(self.filePath)[1]
				node = QtWidgets.QTreeWidgetItem([filename])
				self.ui.treeLoadedFiles.addTopLevelItem(node)
				# Load contents in raw display tab
				filecontents = open(self.filePath,"r").read()
				
				data = pd.DataFrame(data=[[str(filename), filecontents]],columns=["filename","contents"])
				# Add file to HDF
				self.hdf5_file.append('raw', data)
								
				self.ui.textboxRawFile.clear()
				self.ui.textboxRawFile.insertPlainText(filecontents)
				# Make sure the messages are immediately shown
				QtCore.QCoreApplication.instance().processEvents()
			else:
				raise IOError("Invalid file selected")
	
	
	def importFiles(self):
		# Import raw datafiles, start in home folder of user
		self.fileName = QtWidgets.QFileDialog.getOpenFileName(self, "Import Files", QtCore.QDir.homePath())
		
	def toggleDockWidget(self, checked):	
		sender_name = self.sender().objectName()
		if type(self.sender()) == QtWidgets.QDockWidget:
			toggle_action = "toggle" + sender_name[0].upper() + sender_name[1:]
			menuItem = self.ui.findChild(QtWidgets.QAction, toggle_action)
			menuItem.setChecked(checked)
		
		if type(self.sender()) == QtWidgets.QAction:
			sender_name = sender_name.replace("toggle","")
			dockWidget = self.ui.findChild(QtWidgets.QWidget, sender_name[0].lower() + sender_name[1:])
			dockWidget.setVisible(checked)
	
	def setDockWidgetVisibility(self, status):
		if type(self.sender()) == QtWidgets.QDockWidget:
			if status:
				self.toggleDockWidget(True)
			else:
				self.toggleDockWidget(False)
		
if __name__ == "__main__":
	OpenEyesGUI()
	
	